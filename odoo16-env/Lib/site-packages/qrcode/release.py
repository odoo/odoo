"""
This file provides zest.releaser entrypoints using when releasing new
qrcode versions.
"""

import os
import re
import datetime


def update_manpage(data):
    """
    Update the version in the manpage document.
    """
    if data["name"] != "qrcode":
        return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filename = os.path.join(base_dir, "doc", "qr.1")
    with open(filename) as f:
        lines = f.readlines()

    changed = False
    for i, line in enumerate(lines):
        if not line.startswith(".TH "):
            continue
        parts = re.split(r'"([^"]*)"', line)
        if len(parts) < 5:
            continue
        changed = parts[3] != data["new_version"]
        if changed:
            # Update version
            parts[3] = data["new_version"]
            # Update date
            parts[1] = datetime.datetime.now().strftime("%-d %b %Y")
            lines[i] = '"'.join(parts)
        break

    if changed:
        with open(filename, "w") as f:
            for line in lines:
                f.write(line)
