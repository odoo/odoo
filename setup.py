#!/usr/bin/env python
# ruff: noqa: F821
# (ruff don't see read variables from release.py)

import pathlib
from os.path import dirname, join

from setuptools import find_namespace_packages, setup

exec(pathlib.Path(join(pathlib.Path(__file__).parent, 'odoo', 'release.py')).open('rb').read())  # Load release variables
lib_name = 'odoo'

setup(
    name='odoo',
    version=version,
    description=description,
    long_description=long_desc,
    url=url,
    author=author,
    author_email=author_email,
    classifiers=[c for c in classifiers.split('\n') if c],
    license=license,
    scripts=['setup/odoo'],
    packages=find_namespace_packages(),
    package_dir={'%s' % lib_name: 'odoo'},
    include_package_data=True,
    install_requires=[
        'asn1crypto',
        'babel >= 1.0',
        'cbor2',
        'chardet',
        'cryptography',
        'docutils',
        'geoip2',
        'idna',
        'Jinja2',
        'lxml',  # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
        'lxml_html_clean',
        'MarkupSafe',
        'num2words',
        'ofxparse',
        'openpyxl',
        'pillow',  # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
        'polib',
        'protobuf',
        'psutil',  # windows binary code.google.com/p/psutil/downloads/list
        'psycopg[binary] >= 3.3.2',
        'pyopenssl',
        'pypdf',
        'pyserial',
        'python-dateutil',
        'python-stdnum',
        'pytz',
        'pyusb >= 1.0.0b1',
        'qrcode',
        'reportlab',  # windows binary pypi.python.org/pypi/reportlab
        'rjsmin',
        'requests',
        'urllib3',
        'vobject',
        'werkzeug',
        'xlsxwriter',
        'zeep',
    ],
    python_requires='>=' + ".".join(map(str, MIN_PY_VERSION)),
    extras_require={
        'ldap': ['python-ldap'],
    },
    tests_require=[
        'freezegun',
    ],
)
