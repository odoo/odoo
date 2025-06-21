"""adodbapi -- a pure Python PEP 249 DB-API package using Microsoft ADO

Adodbapi can be run on CPython 3.5 and later.
"""

NAME = "adodbapi"
MAINTAINER = "Vernon Cole"
MAINTAINER_EMAIL = "vernondcole@gmail.com"
DESCRIPTION = (
    """A pure Python package implementing PEP 249 DB-API using Microsoft ADO."""
)
URL = "https://sourceforge.net/projects/adodbapi"
LICENSE = "LGPL"
CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: SQL",
    "Topic :: Software Development",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Database",
]
AUTHOR = "Henrik Ekelund, Vernon Cole, et.al."
AUTHOR_EMAIL = "vernondcole@gmail.com"
PLATFORMS = ["Windows", "Linux"]

VERSION = None  # in case searching for version fails
a = open("adodbapi.py")  # find the version string in the source code
for line in a:
    if "__version__" in line:
        VERSION = line.split("'")[1]  # pyright: ignore[reportConstantRedefinition]
        print('adodbapi version="%s"' % VERSION)
        break
a.close()


def setup_package():
    from setuptools import setup
    from setuptools.command.build_py import build_py

    setup(
        cmdclass={"build_py": build_py},
        name=NAME,
        maintainer=MAINTAINER,
        maintainer_email=MAINTAINER_EMAIL,
        description=DESCRIPTION,
        url=URL,
        keywords="database ado odbc dbapi db-api Microsoft SQL",
        ##        download_url=DOWNLOAD_URL,
        long_description=open("README.txt").read(),
        license=LICENSE,
        classifiers=CLASSIFIERS,
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        platforms=PLATFORMS,
        version=VERSION,
        package_dir={"adodbapi": ""},
        packages=["adodbapi"],
    )
    return


if __name__ == "__main__":
    setup_package()
