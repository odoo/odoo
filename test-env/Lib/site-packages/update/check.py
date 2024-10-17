from __future__ import print_function

import json
import os
import style
import urllib

from distutils.version import StrictVersion


def check(package):
    '''
    '''
    package_info = None
    newest_version = StrictVersion(package_info['info']['version'])
    current_version = StrictVersion(__version__)
    if newest_version > current_version:
        _print_update_instructions(package)


def check_version(package):
    '''
    '''
    filehandle = urllib.urlopen('https://pypi.python.org/pypi/%s/json' % package)


def _print_update_instructions(package):
    '''
    '''
    print(style.yellow('A new version of', style.bold(package), 'is available.\nRun',
                       style.bold('pip install -U', package), 'to upgrade.'), end='\n'*2)
