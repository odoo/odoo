# -*- coding: utf-8 -*-
# Support functions for travis
# See https://github.com/travis-ci/travis-rubies/blob/9f7962a881c55d32da7c76baefc58b89e3941d91/build.sh

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys


commands = {}

def command(func):
    commands[func.__name__] = lambda: func(*sys.argv[2:])
    return func

@command
def fold_start(name, msg):
    sys.stdout.write('travis_fold:start:')
    sys.stdout.write(name)
    sys.stdout.write(chr(0o33))
    sys.stdout.write('[33;1m')
    sys.stdout.write(msg)
    sys.stdout.write(chr(0o33))
    sys.stdout.write('[33;0m\n')

@command
def fold_end(name):
    sys.stdout.write("\ntravis_fold:end:")
    sys.stdout.write(name)
    sys.stdout.write("\r\n")


def main():
    cmd = sys.argv[1]
    commands[cmd]()


if __name__ == '__main__':
    main()
