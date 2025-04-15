import os
import tempfile
import unittest

import win32com.test.util

expected_output = "The jscript test worked.\nThe Python test worked"


class XSLT(win32com.test.util.TestCase):
    def testAll(self):
        output_name = tempfile.mktemp("-pycom-test")
        cmd = (
            "cscript //nologo testxslt.js doesnt_matter.xml testxslt.xsl " + output_name
        )
        win32com.test.util.ExecuteShellCommand(cmd, self)
        try:
            f = open(output_name)
            try:
                got = f.read()
                if got != expected_output:
                    print(f"ERROR: XSLT expected output of {expected_output!r}")
                    print(f"but got {got!r}")
            finally:
                f.close()
        finally:
            try:
                os.unlink(output_name)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
