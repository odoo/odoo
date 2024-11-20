#!/usr/bin/python2
# Configure this in order to run the testcases.
"setuptestframework.py v 2.6.0.8"
import os
import shutil
import tempfile


def maketemp():
    temphome = tempfile.gettempdir()
    tempdir = os.path.join(temphome, "adodbapi_test")
    try:
        os.mkdir(tempdir)
    except:
        pass
    return tempdir


def _cleanup_function(testfolder, mdb_name):
    try:
        os.unlink(os.path.join(testfolder, mdb_name))
    except:
        pass  # mdb database not present
    try:
        shutil.rmtree(testfolder)
        print("   cleaned up folder", testfolder)
    except:
        pass  # test package not present


def getcleanupfunction():
    return _cleanup_function


def find_ado_path():
    adoName = os.path.normpath(os.getcwd() + "/../../adodbapi.py")
    adoPackage = os.path.dirname(adoName)
    return adoPackage


# make a new package directory for the test copy of ado
def makeadopackage(testfolder):
    adoName = os.path.normpath(os.getcwd() + "/../adodbapi.py")
    adoPath = os.path.dirname(adoName)
    if os.path.exists(adoName):
        newpackage = os.path.join(testfolder, "adodbapi")
        try:
            os.makedirs(newpackage)
        except OSError:
            print(
                "*Note: temporary adodbapi package already exists: may be two versions running?"
            )
        for f in os.listdir(adoPath):
            if f.endswith(".py"):
                shutil.copy(os.path.join(adoPath, f), newpackage)
        return testfolder
    else:
        raise OSError("Connot find source of adodbapi to test.")


def makemdb(testfolder, mdb_name):
    # following setup code borrowed from pywin32 odbc test suite
    # kindly contributed by Frank Millman.
    import os

    _accessdatasource = os.path.join(testfolder, mdb_name)
    if os.path.isfile(_accessdatasource):
        print("using JET database=", _accessdatasource)
    else:
        from win32com.client import constants
        from win32com.client.gencache import EnsureDispatch

        # Create a brand-new database - what is the story with these?
        dbe = None
        for suffix in (".36", ".35", ".30"):
            try:
                dbe = EnsureDispatch("DAO.DBEngine" + suffix)
                break
            except:
                pass
        if dbe:
            print("    ...Creating ACCESS db at " + _accessdatasource)
            workspace = dbe.Workspaces(0)
            newdb = workspace.CreateDatabase(
                _accessdatasource, constants.dbLangGeneral, constants.dbVersion40
            )
            newdb.Close()
        else:
            print("    ...copying test ACCESS db to " + _accessdatasource)
            mdbName = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "examples", "test.mdb")
            )
            import shutil

            shutil.copy(mdbName, _accessdatasource)

    return _accessdatasource
