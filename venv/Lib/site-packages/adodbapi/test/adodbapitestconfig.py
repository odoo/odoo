# Configure this to _YOUR_ environment in order to run the testcases.
"testADOdbapiConfig.py v 2.6.2.B00"

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #
# #  TESTERS:
# #
# #  You will need to make numerous modifications to this file
# #  to adapt it to your own testing environment.
# #
# #  Skip down to the next "# #" line --
# #  -- the things you need to change are below it.
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
import platform
import random
import sys

import is64bit
import setuptestframework
import tryconnection

print("\nPython", sys.version)
node = platform.node()
try:
    print(
        "node=%s, is64bit.os()= %s, is64bit.Python()= %s"
        % (node, is64bit.os(), is64bit.Python())
    )
except:
    pass

if "--help" in sys.argv:
    print(
        """Valid command-line switches are:
    --package - create a temporary test package
    --all - run all possible tests
    --time - do time format test
    --nojet - do not test against an ACCESS database file
    --mssql - test against Microsoft SQL server
    --pg - test against PostgreSQL
    --mysql - test against MariaDB
    """
    )
    exit()
try:
    onWindows = bool(sys.getwindowsversion())  # seems to work on all versions of Python
except:
    onWindows = False

# create a random name for temporary table names
_alphabet = (
    "PYFGCRLAOEUIDHTNSQJKXBMWVZ"  # why, yes, I do happen to use a dvorak keyboard
)
tmp = "".join([random.choice(_alphabet) for x in range(9)])
mdb_name = "xx_" + tmp + ".mdb"  # generate a non-colliding name for the temporary .mdb
testfolder = setuptestframework.maketemp()

if "--package" in sys.argv:
    #  create a new adodbapi module
    pth = setuptestframework.makeadopackage(testfolder)
else:
    #  use the adodbapi module in which this file appears
    pth = setuptestframework.find_ado_path()
if pth not in sys.path:
    #  look here _first_ to find modules
    sys.path.insert(1, pth)

# function to clean up the temporary folder -- calling program must run this function before exit.
cleanup = setuptestframework.getcleanupfunction()

import adodbapi  # will (hopefully) be imported using the "pth" discovered above

print(adodbapi.version)  # show version
print(__doc__)

verbose = False
for a in sys.argv:
    if a.startswith("--verbose"):
        arg = True
        try:
            arg = int(a.split("=")[1])
        except IndexError:
            pass
        adodbapi.adodbapi.verbose = arg
        verbose = arg

doAllTests = "--all" in sys.argv
doAccessTest = not ("--nojet" in sys.argv)
doSqlServerTest = "--mssql" in sys.argv or doAllTests
doMySqlTest = "--mysql" in sys.argv or doAllTests
doPostgresTest = "--pg" in sys.argv or doAllTests
doTimeTest = ("--time" in sys.argv or doAllTests) and onWindows

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # start your environment setup here v v v
SQL_HOST_NODE = "testsql.2txt.us,1430"

if doAccessTest:
    c = {
        "mdb": setuptestframework.makemdb(testfolder, mdb_name),
        # macro definition for keyword "provider"  using macro "is64bit" -- see documentation
        # is64bit will return true for 64 bit versions of Python, so the macro will select the ACE provider
        "macro_is64bit": [
            "provider",
            "Microsoft.ACE.OLEDB.12.0",  # 64 bit provider
            "Microsoft.Jet.OLEDB.4.0",  # 32 bit provider
        ],
    }

    # ;Mode=ReadWrite;Persist Security Info=False;Jet OLEDB:Bypass UserInfo Validation=True"
    connStrAccess = "Provider=%(provider)s;Data Source=%(mdb)s"
    print("    ...Testing ACCESS connection to {} file...".format(c["mdb"]))
    doAccessTest, connStrAccess, dbAccessconnect = tryconnection.try_connection(
        verbose, connStrAccess, 10, **c
    )

if doSqlServerTest:
    c = {
        "host": SQL_HOST_NODE,  # name of computer with SQL Server
        "database": "adotest",
        "user": "adotestuser",  # None implies Windows security
        "password": "Sq1234567",
        # macro definition for keyword "security" using macro "auto_security"
        "macro_auto_security": "security",
        "provider": "MSOLEDBSQL; MARS Connection=True",
    }
    connStr = "Provider=%(provider)s; Initial Catalog=%(database)s; Data Source=%(host)s; %(security)s;"
    print("    ...Testing MS-SQL login to {}...".format(c["host"]))
    (
        doSqlServerTest,
        connStrSQLServer,
        dbSqlServerconnect,
    ) = tryconnection.try_connection(verbose, connStr, 30, **c)

if doMySqlTest:
    c = {
        "host": "testmysql.2txt.us",
        "database": "adodbapitest",
        "user": "adotest",
        "password": "12345678",
        "port": "3330",  # note the nonstandard port for obfuscation
        "driver": "MySQL ODBC 5.1 Driver",
    }  # or _driver="MySQL ODBC 3.51 Driver
    c["macro_is64bit"] = [
        "provider",
        "Provider=MSDASQL;",
    ]  # turn on the 64 bit ODBC adapter only if needed
    cs = (
        "%(provider)sDriver={%(driver)s};Server=%(host)s;Port=3330;"
        + "Database=%(database)s;user=%(user)s;password=%(password)s;Option=3;"
    )
    print("    ...Testing MySql login to {}...".format(c["host"]))
    doMySqlTest, connStrMySql, dbMySqlconnect = tryconnection.try_connection(
        verbose, cs, 5, **c
    )


if doPostgresTest:
    _computername = "testpg.2txt.us"
    _databasename = "adotest"
    _username = "adotestuser"
    _password = "12345678"
    kws = {"timeout": 4}
    kws["macro_is64bit"] = [
        "prov_drv",
        "Provider=MSDASQL;Driver={PostgreSQL Unicode(x64)}",
        "Driver=PostgreSQL Unicode",
    ]
    # get driver from https://www.postgresql.org/ftp/odbc/releases/
    # test using positional and keyword arguments (bad example for real code)
    print("    ...Testing PostgreSQL login to {}...".format(_computername))
    doPostgresTest, connStrPostgres, dbPostgresConnect = tryconnection.try_connection(
        verbose,
        "%(prov_drv)s;Server=%(host)s;Database=%(database)s;uid=%(user)s;pwd=%(password)s;port=5430;",  # note nonstandard port
        _username,
        _password,
        _computername,
        _databasename,
        **kws,
    )

assert (
    doAccessTest or doSqlServerTest or doMySqlTest or doPostgresTest
), "No database engine found for testing"
