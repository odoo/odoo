# Test AXScripting the best we can in an automated fashion...
import os
import sys

import win32api
import win32com.axscript
import win32com.axscript.client
import win32com.test.util

verbose = "-v" in sys.argv


class AXScript(win32com.test.util.TestCase):
    def setUp(self):
        file = win32api.GetFullPathName(
            os.path.join(next(iter(win32com.axscript.client.__path__)), "pyscript.py")
        )

        self.verbose = verbose
        win32com.test.util.RegisterPythonServer(file, "python", verbose=self.verbose)

    def testHost(self):
        file = win32api.GetFullPathName(
            os.path.join(next(iter(win32com.axscript.__path__)), "test\\testHost.py")
        )
        cmd = f'{win32api.GetModuleFileName(0)} "{file}"'
        if verbose:
            print("Testing Python Scripting host")
        win32com.test.util.ExecuteShellCommand(cmd, self)

    def testCScript(self):
        file = win32api.GetFullPathName(
            os.path.join(
                next(iter(win32com.axscript.__path__)), "Demos\\Client\\wsh\\test.pys"
            )
        )
        cmd = 'cscript.exe "%s"' % (file)
        if verbose:
            print("Testing Windows Scripting host with Python script")
        win32com.test.util.ExecuteShellCommand(cmd, self)


if __name__ == "__main__":
    win32com.test.util.testmain()
