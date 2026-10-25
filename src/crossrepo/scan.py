"""Source harvesting: turn a repository tree into structured facts."""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist",
    "build", ".idea", ".vscode", "site-packages", "target", ".next",
}
CODE_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".php", ".swift", ".kt", ".scala", ".sh",
}
MAX_FILE_BYTES = 512_000

IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")


@dataclass
class Symbol:
    """One named thing found in the repository."""

    name: str
    kind: str  # class | function | method | module | constant | identifier
    file: str = ""
    lineno: int = 0
    module: str = ""
    docstring: str = ""
    refs: int = 0


@dataclass
class RepoFacts:
    """Everything CrossRepo learned about a repository."""

    root: Path
    name: str
    mode: str = "python"  # python | generic
    symbols: list[Symbol] = field(default_factory=list)
    total_files: int = 0
    total_loc: int = 0
    sources: dict[str, str] = field(default_factory=dict)  # relpath -> text


def harvest(root: Path) -> RepoFacts:
    """Walk *root* and collect identifier facts from its source files.

    Python files are parsed with :mod:`ast` for precise symbols; if the
    tree contains no Python at all, a language-agnostic tokenizer kicks
    in so any repository still produces a puzzle.
    """
    root = Path(root).resolve()
    facts = RepoFacts(root=root, name=root.name)
    py_files: list[tuple[str, str]] = []
    other_files: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        )
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() not in CODE_EXTS:
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = path.relative_to(root).as_posix()
            facts.sources[rel] = text
            facts.total_files += 1
            facts.total_loc += len(text.splitlines())
            (py_files if path.suffix == ".py" else other_files).append((rel, text))
    if py_files:
        facts.mode = "python"
        for rel, text in py_files:
            _scan_python(rel, text, facts)
        _count_refs(facts)
    else:
        facts.mode = "generic"
        _scan_generic(other_files, facts)
    return facts


def _scan_python(rel: str, text: str, facts: RepoFacts) -> None:
    module = _module_name(rel)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    facts.symbols.append(Symbol(_last(module), "module", rel, 1, module=module))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            facts.symbols.append(Symbol(
                node.name, "function", rel, node.lineno, module=module,
                docstring=_first_sentence(ast.get_docstring(node)),
            ))
        elif isinstance(node, ast.ClassDef):
            facts.symbols.append(Symbol(
                node.name, "class", rel, node.lineno, module=module,
                docstring=_first_sentence(ast.get_docstring(node)),
            ))
            for sub in node.body:
                if (isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not sub.name.startswith("__")):
                    facts.symbols.append(Symbol(
                        sub.name, "method", rel, sub.lineno, module=module,
                        docstring=_first_sentence(ast.get_docstring(sub)),
                    ))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", target.id):
                    facts.symbols.append(Symbol(target.id, "constant", rel, node.lineno, module=module))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", node.target.id):
                facts.symbols.append(Symbol(node.target.id, "constant", rel, node.lineno, module=module))


def _scan_generic(files: list[tuple[str, str]], facts: RepoFacts) -> None:
    counts: dict[str, list] = {}
    for rel, text in files:
        for match in IDENT_RE.finditer(text):
            entry = counts.setdefault(match.group(0), [0, rel])
            entry[0] += 1
    for name, (count, first_file) in sorted(counts.items(), key=lambda kv: (-kv[1][0], kv[0])):
        facts.symbols.append(Symbol(name, "identifier", first_file, 0, refs=count))


def _count_refs(facts: RepoFacts) -> None:
    blob = "\n".join(facts.sources.values())
    for sym in facts.symbols:
        sym.refs = len(re.findall(rf"\b{re.escape(sym.name)}\b", blob))


def _module_name(rel: str) -> str:
    no_ext = rel[:-3] if rel.endswith(".py") else rel
    parts = [p for p in no_ext.split("/") if p]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if len(parts) > 1 and parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts) or rel


def _last(dotted: str) -> str:
    return dotted.rsplit(".", 1)[-1]


def _first_sentence(doc: str | None) -> str:
    if not doc:
        return ""
    first_line = doc.strip().splitlines()[0].strip()
    pieces = re.split(r"(?<=\.)\s", first_line, maxsplit=1)
    return (pieces[0] if pieces and pieces[0] else first_line)[:200]
