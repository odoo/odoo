#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/docs/userguide/genuserguide.py
__version__=''' $Id: genuserguide.py 2900 2006-05-22 21:49:00Z andy $ '''
__doc__ = """
This module contains the script for building the user guide.
"""
def run(pagesize=None, verbose=0, outDir=None):
    import os
    from reportlab.tools.docco.rl_doc_utils import setStory, getStory, RLDocTemplate, defaultPageSize
    from reportlab.tools.docco import rl_doc_utils
    from reportlab.lib.utils import open_and_read, _RL_DIR
    if not outDir: outDir = os.path.join(_RL_DIR,'docs')
    destfn = os.path.join(outDir,'userguide.pdf')
    doc = RLDocTemplate(destfn,pagesize = pagesize or defaultPageSize)

    #this builds the story
    setStory()
    G = {}
    exec 'from reportlab.tools.docco.rl_doc_utils import *' in G, G
    for f in (
        'ch1_intro',
        'ch2_graphics',
        'ch2a_fonts',
        'ch3_pdffeatures',
        'ch4_platypus_concepts',
        'ch5_paragraphs',
        'ch6_tables',
        'ch7_custom',
        'ch9_future',
        'app_demos',
        ):
        exec open_and_read(f+'.py',mode='t') in G, G
    del G

    story = getStory()
    if verbose: print 'Built story contains %d flowables...' % len(story)
    doc.build(story)
    if verbose: print 'Saved "%s"' % destfn

def makeSuite():
    "standard test harness support - run self as separate process"
    from reportlab.test.utils import ScriptThatMakesFileTest
    return ScriptThatMakesFileTest('../docs/userguide', 'genuserguide.py', 'userguide.pdf')

def main():
    import sys
    outDir = filter(lambda x: x[:9]=='--outdir=',sys.argv)
    if outDir:
        outDir = outDir[0]
        sys.argv.remove(outDir)
        outDir = outDir[9:]
    else:
        outDir = None
    verbose = '-s' not in sys.argv
    if not verbose: sys.argv.remove('-s')
    timing = '-timing' in sys.argv
    if timing: sys.argv.remove('-timing')
    prof = '-prof' in sys.argv
    if prof: sys.argv.remove('-prof')

    if len(sys.argv) > 1:
        try:
            pagesize = (w,h) = eval(sys.argv[1])
        except:
            print 'Expected page size in argument 1', sys.argv[1]
            raise
        if verbose:
            print 'set page size to',sys.argv[1]
    else:
        pagesize = None
    if timing:
        from time import time
        t0 = time()
        run(pagesize, verbose,outDir)
        if verbose:
            print 'Generation of userguide took %.2f seconds' % (time()-t0)
    elif prof:
        import profile
        profile.run('run(pagesize,verbose,outDir)','genuserguide.stats')
    else:
        run(pagesize, verbose,outDir)
if __name__=="__main__":
    main()
