# rc2py.py
# This module is part of the spambayes project, which is Copyright 2003
# The Python Software Foundation and is covered by the Python Software
# Foundation license.
__author__="Adam Walker"
__doc__=""""
Converts an .rc windows resource source file into a python source file
with the same basic public interface as the rcparser module.
"""
import sys, os, stat
import rcparser

def convert(inputFilename = None, outputFilename = None):
    """See the module doc string"""
    if inputFilename is None:
        inputFilename = "dialogs.rc"
    if outputFilename is None:
        outputFilename = "test.py"
    rcp = rcparser.ParseDialogs(inputFilename)
    in_stat = os.stat(inputFilename)

    out = open(outputFilename, "wt")
    out.write("#%s\n" % outputFilename)
    out.write("#This is a generated file. Please edit %s instead.\n" % inputFilename)
    out.write("_rc_size_=%d\n_rc_mtime_=%d\n" % (in_stat[stat.ST_SIZE], in_stat[stat.ST_MTIME]))
    out.write("class FakeParser:\n")
    out.write("\tdialogs = "+repr(rcp.dialogs)+"\n")
    out.write("\tids = "+repr(rcp.ids)+"\n")
    out.write("\tnames = "+repr(rcp.names)+"\n")
    out.write("\tbitmaps = "+repr(rcp.bitmaps)+"\n")
    out.write("def ParseDialogs(s):\n")
    out.write("\treturn FakeParser()\n")
    out.close()

if __name__=="__main__":
    if len(sys.argv)>1:
        convert(sys.argv[1], sys.argv[2])
    else:
        convert()
