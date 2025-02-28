#!/usr/bin/env python3

import re
import sys
from io import StringIO
from collections import defaultdict
from pathlib import Path


if sys.argv[-1] == sys.argv[0]:
    sys.exit("Usage: inliner.py <file.py>")

filename = sys.argv[-1]
path = Path(filename)
if not path.exists():
    sys.exit(f"Filename {filename} not found")


print(f"<<< Inlining {path}...")


repo = {}
out = StringIO()
outpath = Path("./pdf417gen.py")
imports_repo = defaultdict(list)


def get_matches(line):
    if match := re.match(r"from ([^ ]+) import (.+)", line):
        lib = match.group(1).strip()
        tokens = [x.strip() for x in match.group(2).split(",")]
        return lib, tokens
    if match := re.match(r"import ([^ ]+)", line):
        lib = match.group(1).strip()
        return lib, [None]


header, post_header = StringIO(), StringIO()
with outpath.open("r") as infile:
    target = header
    for idx, line in enumerate(infile):
        if line == '"""\n' and idx > 0:
            target.write(line)
            target = post_header
        else:
            if target == post_header:
                if match := get_matches(line):
                    lib, tokens = match
                    imports_repo[lib] += tokens
                    continue
            target.write(line)
    header.seek(0)
    post_header.seek(0)


with path.open("r") as infile:
    for line in infile:
        if match := get_matches(line):
            lib, tokens = match
            imports_repo[lib] += tokens
            continue
        if match := re.match(r"def (?<!il_)([^(]+)\(", line):
            old = match.group(1)
            new = f'il_{path.stem}_{old}'
            repo[old] = new


with path.open("r") as infile:
    for line in infile:
        if match := get_matches(line):
            continue
        for old, new in repo.items():
            if old in line:
                after = re.sub(old + '\(', new + '(', line)
                print(f'{old} -> {new}  {line.rstrip()}')
                line = after
        out.write(line.rstrip() + '\n')
    out.seek(0)


imports_header = []
for key, values in imports_repo.items():
    if None in values:
        imports_header.append(f"import {key}\n")
    tokens = [x for x in values if x]
    if tokens:
        imports_header.append(f"from {key} import {', '.join(tokens)}\n")
imports_header = '\n\n' + "".join(sorted(imports_header)) + '\n\n\n'


with outpath.open("w") as outfile:
    empty_count = 0
    def write(empty_count, line):
        if not line.strip():
            empty_count += 1
        else:
            empty_count = 0
        if empty_count == 3:
            empty_count = 2
        else:
            outfile.write(line)
        return empty_count

    for line in header:
        empty_count = write(empty_count, line)
    for line in imports_header:
        empty_count = write(empty_count, line)
    for line in post_header:
        empty_count = write(empty_count, line)
    for line in out:
        empty_count = write(empty_count, line)

print(">>> Inlining done.")
