#
# bulkstamp.py:
#    Stamp versions on all files that can be found in a given tree.
#
# USAGE: python bulkstamp.py <version> <root directory> <descriptions>
#
# Example: python bulkstamp.py 103 ..\win32\Build\ desc.txt
#
# <version> corresponds to the build number. It will be concatenated with
# the major and minor version numbers found in the description file.
#
# Description information is pulled from an input text file with lines of
# the form:
#
#    <basename> <white space> <description>
#
# For example:
#
#    PyWinTypes.dll Common types for Python on Win32
#    etc
#
# The product's name, major, and minor versions are specified as:
#
#    name <white space> <value>
#    major <white space> <value>
#    minor <white space> <value>
#
# The tags are case-sensitive.
#
# Any line beginning with "#" will be ignored. Empty lines are okay.
#

import fnmatch
import os
import sys
from collections.abc import Mapping
from optparse import Values

try:
    import win32verstamp
except ModuleNotFoundError:
    # If run with pywin32 not already installed
    sys.path.append(os.path.abspath(__file__ + "/../../../Lib"))
    import win32verstamp

g_patterns = [
    "*.dll",
    "*.pyd",
    "*.exe",
    "*.ocx",
]


def walk(vars: Mapping[str, str], debug, descriptions, dirname, names) -> int:
    """Returns the number of stamped files."""
    numStamped = 0
    for name in names:
        for pat in g_patterns:
            if fnmatch.fnmatch(name, pat):
                # Handle the "_d" thing.
                pathname = os.path.join(dirname, name)
                base, ext = os.path.splitext(name)
                if base.endswith("_d"):
                    name = base[:-2] + ext
                is_dll = ext.lower() != ".exe"
                if os.path.normcase(name) in descriptions:
                    description = descriptions[os.path.normcase(name)]
                    try:
                        options = Values(
                            {**vars, "description": description, "dll": is_dll}
                        )
                        win32verstamp.stamp(pathname, options)
                        numStamped += 1
                    except OSError as exc:
                        print(
                            "Could not stamp",
                            pathname,
                            "Error",
                            exc.winerror,
                            "-",
                            exc.strerror,
                        )
                else:
                    print("WARNING: description not provided for:", name)
                    # skip branding this - assume already branded or handled elsewhere
    return numStamped


# print("Stamped", pathname)


def load_descriptions(fname, vars):
    retvars: dict[str, str] = {}
    descriptions = {}

    lines = open(fname, "r").readlines()

    for i in range(len(lines)):
        line = lines[i].strip()
        if line != "" and line[0] != "#":
            idx1 = line.find(" ")
            idx2 = line.find("\t")
            if idx1 == -1 or idx2 < idx1:
                idx1 = idx2
            if idx1 == -1:
                print("ERROR: bad syntax in description file at line %d." % (i + 1))
                sys.exit(1)

            key = line[:idx1]
            val = line[idx1:].strip()
            if key in vars:
                retvars[key] = val
            else:
                descriptions[key] = val

    if "product" not in retvars:
        print("ERROR: description file is missing the product name.")
        sys.exit(1)
    if "major" not in retvars:
        print("ERROR: description file is missing the major version number.")
        sys.exit(1)
    if "minor" not in retvars:
        print("ERROR: description file is missing the minor version number.")
        sys.exit(1)

    return retvars, descriptions


def scan(build, root: str, desc, **custom_vars):
    try:
        build = int(build)
    except ValueError:
        print("ERROR: build number is not a number: %s" % build)
        sys.exit(1)

    debug = 0  ### maybe fix this one day

    varList = ["major", "minor", "sub", "company", "copyright", "trademarks", "product"]

    vars, descriptions = load_descriptions(desc, varList)
    vars["build"] = build
    vars.update(custom_vars)

    numStamped = 0
    for directory, dirnames, filenames in os.walk(root):
        numStamped += walk(vars, debug, descriptions, directory, filenames)

    print(f"Stamped {numStamped} files.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("ERROR: incorrect invocation. See script's header comments.")
        sys.exit(1)

    scan(*sys.argv[1:])
