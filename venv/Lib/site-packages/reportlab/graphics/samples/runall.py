# runs all the GUIedit charts in this directory -
# makes a PDF sample for eaxh existing chart type
import sys
import glob
import inspect

def moduleClasses(mod):
    def P(obj, m=mod.__name__, CT=type):
        return (type(obj)==CT and obj.__module__==m)
    try:
        return inspect.getmembers(mod, P)[0][1]
    except:
        return None

def getclass(f):
    return moduleClasses(__import__(f))

def run(format, VERBOSE=0):
    formats = format.split( ',')
    for i in range(0, len(formats)):
        formats[i] == formats[i].strip().lower()
    allfiles = glob.glob('*.py')
    allfiles.sort()
    for fn in allfiles:
        f = fn.split('.')[0]
        c = getclass(f)
        if c != None:
            print(c.__name__)
            try:
                for fmt in formats:
                    if fmt:
                        c().save(formats=[fmt],outDir='.',fnRoot=c.__name__)
                        if VERBOSE:
                            print("  %s.%s" % (c.__name__, fmt))
            except:
                print("  COULDN'T CREATE '%s.%s'!" % (c.__name__, format))

if __name__ == "__main__":
    if len(sys.argv) == 1:
        run('pdf,pict,png')
    else:
        try:
            if sys.argv[1] == "-h":
                print('usage: runall.py [FORMAT] [-h]')
                print('   if format is supplied is should be one or more of pdf,gif,eps,png etc')
                print('   if format is missing the following formats are assumed: pdf,pict,png')
                print('   -h prints this message')
            else:
                t = sys.argv[1:]
                for f in t:
                    run(f)
        except:
            print('usage: runall.py [FORMAT][-h]')
            print('   if format is supplied is should be one or more of pdf,gif,eps,png etc')
            print('   if format is missing the following formats are assumed: pdf,pict,png')
            print('   -h prints this message')
            raise
