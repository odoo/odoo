"""
Search for Gruntfile.js files in all the addons and launch them using the 'grunt test' command.
"""

import common
import fnmatch
import os
import re
import sys
import subprocess

def grunt_tester(directories, log = sys.stdout):
    result = 0

    matches = []
    for direc in directories:
        for root, dirnames, filenames in os.walk(direc):
            for filename in fnmatch.filter(filenames, 'Gruntfile.js'):
                full = os.path.join(root, filename)
                if re.match(r"(^.*?/node_modules/.*$)|(^.*?/lib/.*$)", full):
                    continue
                matches.append(full)

    for file_ in matches:
        folder = os.path.dirname(file_)
        p = subprocess.Popen(['npm', 'install'], cwd=folder)
        if p.wait() != 0:
            raise Exception("Failed to install dependencies for Gruntfile located in folder %s" % folder)

        p = subprocess.Popen(['grunt', 'test', '--no-color'], cwd=folder, stdout=log, stderr=log)
        if p.wait() != 0:
            result = 1

    return result

def run(args):
    if args.addons:
        args.addons = args.addons.split(':')
    else:
        args.addons = []
    result = grunt_tester(args.addons)
    if result != 0:
        sys.exit(result)

def add_parser(subparsers):
    parser = subparsers.add_parser('grunt-tests',
        description='Run the tests contained in Gruntfile.js files.')
    common.add_addons_argument(parser)

    parser.set_defaults(run=run)
