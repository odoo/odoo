#!/usr/bin/env python
# ruff: noqa: F821
# (ruff don't see read variables from release.py)

import pathlib

from setuptools import find_namespace_packages, setup

exec(
    (pathlib.Path(__file__).parent / "odoo" / "release.py").open("rb").read()
)  # Load release variables
lib_name = "odoo"

LONG_DESCRIPTION = """\
Odoo is a complete ERP and CRM. The main features are accounting (analytic
and financial), stock management, sales and purchases management, tasks
automation, marketing campaigns, help desk, POS, etc. Technical features include
a distributed server, an object database, a dynamic GUI,
customizable reports, and XML-RPC interfaces.
"""

CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Programming Language :: Python",
]

setup(
    name="odoo",
    version=version,
    description=description,
    long_description=LONG_DESCRIPTION,
    url=url,
    author=author,
    author_email="info@odoo.com",
    classifiers=CLASSIFIERS,
    license="LGPL-3.0-only",
    scripts=["setup/odoo"],
    packages=find_namespace_packages(include=["odoo*", "addons*"]),
    package_dir={"%s" % lib_name: "odoo"},
    include_package_data=True,
    # Keep in lockstep with requirements.txt — the two had drifted apart, and a
    # dependency listed in only one of them is a dependency that goes missing in
    # whichever install path reads the other. install_requires mirrors
    # requirements.txt (the server); the `addons` extra mirrors
    # requirements-addons.txt (dependencies owned by individual modules).
    install_requires=[
        "asn1crypto",
        "babel >= 1.0",
        "beautifulsoup4",
        "blake3",
        "cbor2",
        "cryptography",
        # Both arrive with weasyprint, but web/models/ir_actions_report.py
        # imports them directly — cssselect2 unguarded at module scope. Declared for the
        # reason recorded in requirements.txt: a transitive dependency is not a
        # contract.
        "cssselect2",
        "docutils",
        "fonttools",
        "geoip2",
        "idna",
        "lxml",  # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
        "lxml_html_clean",
        "MarkupSafe",
        # http/geoip.py imports it directly, not only through geoip2.
        "maxminddb",
        "num2words",
        "orjson",
        # modules/module.py parses external_dependencies specifiers with it.
        "packaging",
        "pillow",  # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
        "polib",
        # Bounded for the reason recorded in requirements.txt: the vendored SCSS
        # gencode rejects a runtime whose major is below its 6.31.1 stamp.
        "protobuf >= 6.31.0, < 8",
        "psutil",  # windows binary code.google.com/p/psutil/downloads/list
        "psycopg[binary] >= 3.3.4",
        "psycopg-pool >= 3.3.1",
        "pyopenssl",
        "pypdf",
        "python-dateutil",
        "python-magic ; sys_platform != 'win32'",
        "reportlab",  # windows binary pypi.python.org/pypi/reportlab
        "rjsmin",
        "requests",
        "rl-renderPM ; sys_platform == 'win32'",
        "rlPyCairo",
        "urllib3",
        "weasyprint",
        "werkzeug",
        "xlsxwriter",
    ],
    python_requires=">=" + ".".join(map(str, MIN_PY_VERSION)),
    extras_require={
        "ldap": ["python-ldap"],
        # AGPL-3.0-or-commercial, and base/ir_actions_report already guards the
        # import — so it is offered rather than imposed.
        "pdf-raster": ["PyMuPDF"],
        # `odoo-bin scaffold` renders its module templates through Jinja2, and
        # nothing else does. cli/__init__ imports a command module only when
        # that command is dispatched, and cli/scaffold.py builds its environment
        # lazily, so a server never reaches the import. It sat in
        # install_requires until 2026-08-08, which put a developer command's
        # dependency on every production install.
        "scaffold": ["Jinja2"],
        # Everything requirements-addons.txt pins: the dependencies of the
        # bundled addons, which the server itself never imports. `ldap` and
        # `pdf-raster` stay separate because they were already published under
        # those names.
        "addons": [
            "chardet",
            "defusedxml",
            "google-auth",
            "odfpy",
            "openpyxl",
            "pdfminer.six",
            "phonenumbers",
            "PyMuPDF",
            "python-ldap ; sys_platform != 'win32'",
            "python-stdnum",
            "qrcode",
            "vobject",
            "xlrd",
            "zeep",
        ],
    },
)
