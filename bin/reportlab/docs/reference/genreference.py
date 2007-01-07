#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/docs/reference/genreference.py
__version__=''' $Id: genreference.py 2385 2004-06-17 15:26:05Z rgbecker $ '''
__doc__ = """
This module contains the script for building the reference.
"""
def run(verbose=None, outDir=None):
    import os, sys, shutil
    from reportlab.tools.docco import yaml2pdf
    from reportlab.lib.utils import _RL_DIR
    if verbose is None: verbose=('-s' not in sys.argv)
    yaml2pdf.run('reference.yml','reference.pdf')
    if verbose: print 'Saved reference.pdf'
    docdir = os.path.join(_RL_DIR,'docs')
    if outDir: docDir = outDir
    destfn = docdir + os.sep + 'reference.pdf'
    shutil.copyfile('reference.pdf', destfn)
    if verbose: print 'copied to %s' % destfn

def makeSuite():
    "standard test harness support - run self as separate process"
    from reportlab.test.utils import ScriptThatMakesFileTest
    return ScriptThatMakesFileTest('../docs/reference', 'genreference.py', 'reference.pdf')


if __name__=='__main__':
    run()
