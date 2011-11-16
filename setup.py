
import os
import re
import sys
from setuptools import setup, find_packages

execfile('addons/web/common/release.py')

version_dash_incompatible = False
if 'bdist_rpm' in sys.argv:
    version_dash_incompatible = True
try:
    import py2exe
    from py2exe_utils import opts
    version_dash_incompatible = True
except ImportError:
    opts = {}
if version_dash_incompatible:
    version = version.split('-')[0]

FILE_PATTERNS = \
    r'.+\.(py|cfg|po|pot|mo|txt|rst|gif|png|jpg|ico|mako|html|js|css|htc|swf)$'
def find_data_files(source, patterns=FILE_PATTERNS):
    file_matcher = re.compile(patterns, re.I)
    out = []
    for base, _, files in os.walk(source):
        cur_files = []
        for f in files:
            if file_matcher.match(f):
                cur_files.append(os.path.join(base, f))
        if cur_files:
            out.append(
                (base, cur_files))

    return out

setup(
    name=name,
    version=version,
    description=description,
    long_description=long_description,
    author=author,
    author_email=author_email,
    url=url,
    download_url=download_url,
    license=license,
    install_requires=[
        "Babel >= 0.9.6",
        "simplejson >= 2.0.9",
        "python-dateutil >= 1.4.1",
        "pytz",
        "werkzeug == 0.7",
    ],
    tests_require=[
        'unittest2',
        'mock',
    ],
    test_suite = 'unittest2.collector',
    zip_safe=False,
    packages=find_packages(),
    classifiers=[
        'Development Status :: 6 - Production/Stable',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Environment :: Web Environment',
        'Topic :: Office/Business :: Financial',
        ],
    scripts=['openerp-web'],
    data_files=(find_data_files('addons')
              + opts.pop('data_files', [])
    ),
    **opts
)
