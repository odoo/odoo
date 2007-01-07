#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/tools/docco/codegrab.py
#codegrab.py
"""
This grabs various Python class, method and function
headers and their doc strings to include in documents
"""

import imp
import types
import string
import os
import sys

class Struct:
    pass

def getObjectsDefinedIn(modulename, directory=None):
    """Returns two tuple of (functions, classes) defined
    in the given module.  'directory' must be the directory
    containing the script; modulename should not include
    the .py suffix"""

    if directory:
        searchpath = [directory]
    else:
        searchpath = sys.path   # searches usual Python path

    #might be a package.  If so, check the top level
    #package is there, then recalculate the path needed
    words = string.split(modulename, '.')
    if len(words) > 1:
        packagename = words[0]
        packagefound = imp.find_module(packagename, searchpath)
        assert packagefound, "Package %s not found" % packagename
        (file, packagepath, description) = packagefound
        #now the full path should be known, if it is in the
        #package

        directory = apply(os.path.join, tuple([packagepath] + words[1:-1]))
        modulename = words[-1]
        searchpath = [directory]



    #find and import the module.
    found = imp.find_module(modulename, searchpath)
    assert found, "Module %s not found" % modulename
    (file, pathname, description) = found
    mod = imp.load_module(modulename, file, pathname, description)

    #grab the code too, minus trailing newlines
    lines = open(pathname, 'r').readlines()
    lines = map(string.rstrip, lines)

    result = Struct()
    result.functions = []
    result.classes = []
    result.doc = mod.__doc__
    for name in dir(mod):
        value = getattr(mod, name)
        if type(value) is types.FunctionType:
            path, file = os.path.split(value.func_code.co_filename)
            root, ext = os.path.splitext(file)
            #we're possibly interested in it
            if root == modulename:
                #it was defined here
                funcObj = value
                fn = Struct()
                fn.name = name
                fn.proto = getFunctionPrototype(funcObj, lines)
                if funcObj.__doc__:
                    fn.doc = dedent(funcObj.__doc__)
                else:
                    fn.doc = '(no documentation string)'
                #is it official?
                if name[0:1] == '_':
                    fn.status = 'private'
                elif name[-1] in '0123456789':
                    fn.status = 'experimental'
                else:
                    fn.status = 'official'

                result.functions.append(fn)
        elif type(value) == types.ClassType:
            if value.__module__ == modulename:
                cl = Struct()
                cl.name = name
                if value.__doc__:
                    cl.doc = dedent(value.__doc__)
                else:
                    cl.doc = "(no documentation string)"

                cl.bases = []
                for base in value.__bases__:
                    cl.bases.append(base.__name__)
                if name[0:1] == '_':
                    cl.status = 'private'
                elif name[-1] in '0123456789':
                    cl.status = 'experimental'
                else:
                    cl.status = 'official'

                cl.methods = []
                #loop over dict finding methods defined here
                # Q - should we show all methods?
                # loop over dict finding methods defined here
                items = value.__dict__.items()
                items.sort()
                for (key2, value2) in items:
                    if type(value2) <> types.FunctionType:
                        continue # not a method
                    elif os.path.splitext(value2.func_code.co_filename)[0] == modulename:
                        continue # defined in base class
                    else:
                        #we want it
                        meth = Struct()
                        meth.name = key2
                        name2 = value2.func_code.co_name
                        meth.proto = getFunctionPrototype(value2, lines)
                        if name2!=key2:
                            meth.doc = 'pointer to '+name2
                            meth.proto = string.replace(meth.proto,name2,key2)
                        else:
                            if value2.__doc__:
                                meth.doc = dedent(value2.__doc__)
                            else:
                                meth.doc = "(no documentation string)"
                        #is it official?
                        if key2[0:1] == '_':
                            meth.status = 'private'
                        elif key2[-1] in '0123456789':
                            meth.status = 'experimental'
                        else:
                            meth.status = 'official'
                        cl.methods.append(meth)
                result.classes.append(cl)
    return result

def getFunctionPrototype(f, lines):
    """Pass in the function object and list of lines;
    it extracts the header as a multiline text block."""
    firstLineNo = f.func_code.co_firstlineno - 1
    lineNo = firstLineNo
    brackets = 0
    while 1:
        line = lines[lineNo]
        for char in line:
            if char == '(':
                brackets = brackets + 1
            elif char == ')':
                brackets = brackets - 1
        if brackets == 0:
            break
        else:
            lineNo = lineNo + 1

    usefulLines = lines[firstLineNo:lineNo+1]
    return string.join(usefulLines, '\n')


def dedent(comment):
    """Attempts to dedent the lines to the edge. Looks at no.
    of leading spaces in line 2, and removes up to that number
    of blanks from other lines."""
    commentLines = string.split(comment, '\n')
    if len(commentLines) < 2:
        cleaned = map(string.lstrip, commentLines)
    else:
        spc = 0
        for char in commentLines[1]:
            if char in string.whitespace:
                spc = spc + 1
            else:
                break
        #now check other lines
        cleaned = []
        for line in commentLines:
            for i in range(min(len(line),spc)):
                if line[0] in string.whitespace:
                    line = line[1:]
            cleaned.append(line)
    return string.join(cleaned, '\n')



def dumpDoc(modulename, directory=None):
    """Test support.  Just prints docco on the module
    to standard output."""
    docco = getObjectsDefinedIn(modulename, directory)
    print 'codegrab.py - ReportLab Documentation Utility'
    print 'documenting', modulename + '.py'
    print '-------------------------------------------------------'
    print
    if docco.functions == []:
        print 'No functions found'
    else:
        print 'Functions:'
        for f in docco.functions:
            print f.proto
            print '    ' + f.doc

    if docco.classes == []:
        print 'No classes found'
    else:
        print 'Classes:'
        for c in docco.classes:
            print c.name
            print '    ' + c.doc
            for m in c.methods:
                print m.proto  # it is already indented in the file!
                print '        ' + m.doc
            print

def test(m='reportlab.platypus.paragraph'):
    dumpDoc(m)

if __name__=='__main__':
    import sys
    print 'Path to search:'
    for line in sys.path:
        print '   ',line
    M = sys.argv[1:]
    if M==[]:
        M.append('reportlab.platypus.paragraph')
    for m in M:
        test(m)