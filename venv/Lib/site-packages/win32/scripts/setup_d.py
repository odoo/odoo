# Install and register pythonXX_d.dll, pywintypesXX_d.dll and pythoncomXX_d.dll
#
# Assumes the _d files can be found in the same directory as this script
# or in the cwd.

import os
import shutil
import sys
import winreg

import win32api


def usage_and_die(rc):
    print()
    print("This script is designed to copy and register the Python debug")
    print("binaries.  It looks for pythonXX_d.dll, pythoncomXX_d.dll etc,")
    print("and installs them to work correctly with Python debug builds.")
    print()
    print("You will generally find this script in the. zip file that")
    print("included these _d files.  Please run this script from")
    print("that directory")
    sys.exit(rc)


if os.path.splitext(os.path.basename(win32api.__file__))[0].endswith("_d"):
    print("This scripts appears to be running a DEBUG version of Python.")
    print("Please run it using a normal release build (python.exe)")
    usage_and_die(1)

try:
    import pythoncom
except ImportError as details:
    print("Could not import the release version of pythoncom")
    print(f"The error details are: {details}")
    print("Please correct this error and rerun the script")
    usage_and_die(2)

try:
    import pywintypes
except ImportError as details:
    print("Could not import the release version of pywintypes")
    print(f"The error details are: {details}")
    print("Please correct this error and rerun the script")
    usage_and_die(2)


def _docopy(src, dest):
    orig_src = src
    if not os.path.isfile(src):
        src = os.path.join(os.path.split(sys.argv[0])[0], src)
        print(
            "Can not find {} or {} to copy".format(
                os.path.abspath(orig_src), os.path.abspath(src)
            )
        )
        return 0
    try:
        shutil.copy(src, dest)
        print(f"Copied {src} -> {dest}")
        return 1
    except:
        print(f"Error copying '{src}' -> '{dest}'")
        print(sys.exc_info()[1])
        usage_and_die(3)


def _doregister(mod_name, dll_name):
    assert os.path.isfile(dll_name), "Shouldn't get here if the file doesn't exist!"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            f"Software\\Python\\PythonCore\\{sys.winver}\\Modules\\{mod_name}",
        )
    except winreg.error:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                f"Software\\Python\\PythonCore\\{sys.winver}\\Modules\\{mod_name}",
            )
        except winreg.error:
            print(
                "Could not find the existing '{}' module registered in the registry".format(
                    mod_name
                )
            )
            usage_and_die(4)
    # Create the debug key.
    sub_key = winreg.CreateKey(key, "Debug")
    winreg.SetValue(sub_key, None, winreg.REG_SZ, dll_name)
    print(f"Registered '{dll_name}' in the registry")


def _domodule(mod_name, release_mod_filename):
    path, fname = os.path.split(release_mod_filename)
    base, ext = os.path.splitext(fname)
    new_fname = base + "_d" + ext
    if _docopy(new_fname, path):
        _doregister(mod_name, os.path.abspath(os.path.join(path, new_fname)))


# First the main Python DLL.
path, fname = path, fname = os.path.split(win32api.GetModuleFileName(sys.dllhandle))
base, ext = os.path.splitext(fname)
_docopy(base + "_d" + ext, path)

# Then pythoncom and pywintypes.
_domodule("pythoncom", pythoncom.__file__)
_domodule("pywintypes", pywintypes.__file__)

print("System _d files were setup.")
