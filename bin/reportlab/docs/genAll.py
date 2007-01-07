#!/bin/env python
import os, sys
def _genAll(d=None,verbose=1):
    if not d: d = '.'
    if not os.path.isabs(d):
        d = os.path.normpath(os.path.join(os.getcwd(),d))
    L = ['reference/genreference.py',
        'userguide/genuserguide.py',
        'graphguide/gengraphguide.py',
        '../tools/docco/graphdocpy.py',
        ]
    if os.path.isdir('../rl_addons'):
        L = L + ['../rl_addons/pyRXP/docs/PyRXP_Documentation.rml']
    elif os.path.isdir('../../rl_addons'):
        L = L + ['../../rl_addons/pyRXP/docs/PyRXP_Documentation.rml']
    for p in L:
        os.chdir(d)
        os.chdir(os.path.dirname(p))
        if p[-4:]=='.rml':
            try:
                from rlextra.rml2pdf.rml2pdf import main
                main(exe=0,fn=[os.path.basename(p)], quiet=not verbose, outDir=d)
            except:
                pass
        else:
            cmd = '%s %s %s' % (sys.executable,os.path.basename(p), not verbose and '-s' or '')
            if verbose: print cmd
            os.system(cmd)

"""Runs the manual-building scripts"""
if __name__=='__main__':
    #need a quiet mode for the test suite
    if '-s' in sys.argv:  # 'silent
        verbose = 0
    else:
        verbose = 1
    _genAll(os.path.dirname(sys.argv[0]),verbose)