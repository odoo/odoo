#!/usr/bin/env python3
"""Write the jsconfig.json of a community or enterprise checkout.

The TypeScript server assigns each file to its nearest jsconfig.json. For the
community files to see the enterprise ones (patches, "models" augmentations,
...) and the other way around, both projects include the files of both
checkouts and an "@module/*" alias for every addon with a static/src folder.
"""

import argparse
import json
import os
import re
from pathlib import Path

TOOLING = Path(__file__).resolve().parent
COMMUNITY = TOOLING.parent.parent.parent
TEMPLATE = TOOLING / "_jsconfig.json"


def relative(path, start):
    rel = Path(os.path.relpath(path, start)).as_posix()
    return rel if rel.startswith("..") else f"./{rel}"


def generate(target, enterprise=None):
    target = target.resolve()
    roots = [COMMUNITY] + ([enterprise.resolve()] if enterprise else [])
    addons_dirs = [COMMUNITY / "addons", COMMUNITY / "odoo/addons"] + roots[1:]

    config = json.loads(TEMPLATE.read_text())
    paths = {}
    for addons_dir in addons_dirs:
        for src in sorted(addons_dir.glob("*/static/src")):
            paths.setdefault(f"@{src.parent.parent.name}/*", [f"{relative(src, target)}/*"])
    config["compilerOptions"]["paths"] = dict(sorted(paths.items()))

    include, exclude = [], []
    for root in roots:
        prefix = "" if root == target else f"{relative(root, target)}/"
        include += [prefix + pattern for pattern in config["include"]]
        exclude += [prefix + pattern for pattern in config["exclude"]]
    config["include"], config["exclude"] = include, exclude

    text = json.dumps(config, indent=4)
    text = re.sub(r'\[\s+("[^"]*")\s+\]', r"[\1]", text)  # one line per alias
    (target / "jsconfig.json").write_text(text + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="checkout where jsconfig.json is written")
    parser.add_argument("--enterprise", type=Path, help="enterprise checkout, if any")
    args = parser.parse_args()
    generate(args.target, args.enterprise)


if __name__ == "__main__":
    main()
