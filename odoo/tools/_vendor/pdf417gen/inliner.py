#!/usr/bin/env python3

import re
import sys
from pathlib import Path

if sys.argv[-1] == sys.argv[0]:
    sys.exit("Usage: inliner.py <file.py>")

filename = sys.argv[-1]
path = Path(filename)
if not path.exists():
    sys.exit(f"Filename {filename} not found")

print(f"<<< Inlining {path}...")

repo = {}
with (
    path.open("r") as infile,
    Path("./pdf417gen.py").open("a") as outfile,
):
    outfile.write("\n\n")
    for line in infile:
        if match := re.match(r"def ([^(]+)", line):
            old = match.group(1)
            new = f'{path.stem}_{old}'
            repo[old] = new
        for old, new in repo.items():
            line = re.sub(old, new, line)
        outfile.write(line)

print(">>> Inlining done.")
