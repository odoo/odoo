from __future__ import annotations

import ast
import pathlib
import re

TEST_PREFIX = "test"


class FileFacts:
    __slots__ = ("bases", "classes", "name", "post_install", "tags", "tests")

    def __init__(self, name: str) -> None:
        self.name = name
        self.tags: list[str] = []
        self.classes: list[str] = []
        self.tests = 0
        self.bases: list[str] = []
        self.post_install = 0


def _tag_args(decorator: ast.expr) -> list[str]:
    if not isinstance(decorator, ast.Call):
        return []
    func = decorator.func
    if (getattr(func, "id", None) or getattr(func, "attr", None)) != "tagged":
        return []
    out = []
    for arg in decorator.args:
        try:
            value = ast.literal_eval(arg)
        except ValueError:
            continue
        if isinstance(value, str):
            out.append(value)
    return out


def _base_names(node: ast.ClassDef) -> list[str]:
    out = []
    for base in node.bases:
        name = getattr(base, "id", None) or getattr(base, "attr", None)
        if name:
            out.append(name)
    return out


def read_test_inventory(tests_dir: pathlib.Path) -> list[FileFacts]:
    facts = []
    for path in sorted(tests_dir.glob("test_*.py")):
        entry = FileFacts(path.name)
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            facts.append(entry)
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            methods = [
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name.startswith(TEST_PREFIX)
            ]
            if not methods:
                continue
            entry.classes.append(node.name)
            entry.tests += len(methods)
            for base in _base_names(node):
                if base not in entry.bases:
                    entry.bases.append(base)
            class_tags = []
            for decorator in node.decorator_list:
                class_tags += _tag_args(decorator)
            if "post_install" in class_tags:
                entry.post_install += 1
            for tag in class_tags:
                if tag not in entry.tags:
                    entry.tags.append(tag)
        facts.append(entry)
    return facts


def existing_descriptions(doc: str) -> dict[str, str]:
    return dict(re.findall(r"^- `(test_[a-z_0-9]+\.py)` — (.+)$", doc, re.MULTILINE))


def render_tagged(facts: list[FileFacts]) -> str:
    tagged = [f for f in facts if f.tags]
    lines = [
        (
            f"### Tagged Files ({len(tagged)} files, "
            f"{sum(len(f.classes) for f in tagged)} classes)"
        ),
        "",
        "| File | Tags | Classes | Tests | Base Class |",
        "|------|------|---------|-------|------------|",
    ]
    lines.extend(
        f"| `{f.name}` | {', '.join(f'`{t}`' for t in f.tags)} | "
        f"{len(f.classes)} | {f.tests} | {', '.join(f.bases) or '—'} |"
        for f in tagged
    )
    return "\n".join(lines)


def render_untagged(facts: list[FileFacts], descriptions: dict[str, str]) -> str:
    untagged = [f for f in facts if not f.tags]
    lines = [
        f"### Untagged Files ({len(untagged)} files)",
        "",
        "These run in **both** at_install and post_install phases by default.",
        "",
    ]
    for f in untagged:
        description = descriptions.get(f.name) or (
            ", ".join(f.classes) if f.classes else "no test class"
        )
        lines.append(f"- `{f.name}` — {description}")
    return "\n".join(lines)


def totals(facts: list[FileFacts]) -> dict[str, int | str]:
    tagged = [f for f in facts if f.tags]
    largest = max(facts, key=lambda f: len(f.classes)) if facts else None
    return {
        "files": len(facts),
        "classes": sum(len(f.classes) for f in facts),
        "tests": sum(f.tests for f in facts),
        "tagged": len(tagged),
        "untagged": len(facts) - len(tagged),
        "post_install": sum(f.post_install for f in facts),
        "unique_tags": len({tag for f in facts for tag in f.tags}),
        "largest": largest.name if largest else "—",
        "largest_classes": len(largest.classes) if largest else 0,
        "largest_tests": largest.tests if largest else 0,
    }


def render_statistics(facts: list[FileFacts]) -> str:
    t = totals(facts)
    pct = round(100 * t["tagged"] / t["files"]) if t["files"] else 0
    rows = [
        ("Total test files", t["files"]),
        ("Total test classes", t["classes"]),
        ("Total test methods", t["tests"]),
        ("Files with @tagged", f"{t['tagged']} ({pct}%)"),
        ("Files without @tagged", f"{t['untagged']} ({100 - pct}%)"),
        ("Classes using post_install", t["post_install"]),
        ("Unique tags", t["unique_tags"]),
        (
            "Largest test file",
            f"{t['largest']} ({t['largest_classes']} classes, {t['largest_tests']} tests)",
        ),
    ]
    lines = ["## Statistics", "", "| Metric | Value |", "|--------|-------|"]
    lines += [f"| {k} | {v} |" for k, v in rows]
    lines += [
        "",
        "Counted as unittest collects them: a method whose name starts with `test`, not",
        "`test_` — a `testCamelCase` method would run too, so it is counted. A class with",
        "no test method is a shared base and is not counted. `factcheck.sh --update`",
        "regenerates every figure above and the header line under Quick Reference.",
    ]
    return "\n".join(lines)


def render(doc: str, facts: list[FileFacts]) -> str:
    descriptions = existing_descriptions(doc)
    t = totals(facts)
    doc = re.sub(
        r"^# All base tests \(.*\)$",
        f"# All base tests ({t['tests']} methods, {t['classes']} classes, "
        f"{t['files']} files)",
        doc,
        count=1,
        flags=re.MULTILINE,
    )
    doc = re.sub(
        r"^### Tagged Files .*?(?=^### Untagged Files )",
        render_tagged(facts) + "\n\n",
        doc,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    doc = re.sub(
        r"^### Untagged Files .*?(?=^## )",
        render_untagged(facts, descriptions) + "\n\n",
        doc,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    return re.sub(
        r"^## Statistics.*?(?=^## )",
        render_statistics(facts) + "\n\n",
        doc,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )


if __name__ == "__main__":
    import sys

    mod = pathlib.Path(sys.argv[1])
    doc_path = mod / "machine_doc_v1" / "TEST_TAGS.md"
    current = doc_path.read_text()
    rendered = render(current, read_test_inventory(mod / "tests"))
    if len(sys.argv) > 2 and sys.argv[2] == "--update":
        if rendered != current:
            doc_path.write_text(rendered)
            print("UPDATED")
        else:
            print("CURRENT")
    else:
        print("CURRENT" if rendered == current else "STALE")
