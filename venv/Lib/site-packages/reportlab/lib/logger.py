#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/logger.py
__version__='3.3.0'
__doc__="Logging and warning framework, predating Python's logging package"
from sys import stderr
class Logger:
    '''
    An extended file type thing initially equivalent to sys.stderr
    You can add/remove file type things; it has a write method
    '''
    def __init__(self):
        self._fps = [stderr]
        self._fns = {}

    def add(self,fp):
        '''add the file/string fp to the destinations'''
        if isinstance(fp,str):
            if fp in self._fns: return
            fp = open(fn,'wb')
            self._fns[fn] = fp
        self._fps.append(fp)

    def remove(self,fp):
        '''remove the file/string fp from the destinations'''
        if isinstance(fp,str):
            if fp not in self._fns: return
            fn = fp
            fp = self._fns[fn]
            del self.fns[fn]
        if fp in self._fps:
            del self._fps[self._fps.index(fp)]

    def write(self,text):
        '''write text to all the destinations'''
        if text[-1]!='\n': text=text+'\n'
        for fp in self._fps: fp.write(text)

    def __call__(self,text):
        self.write(text)

logger=Logger()

class WarnOnce:

    def __init__(self,kind='Warn'):
        self.uttered = {}
        self.pfx = '%s: '%kind
        self.enabled = 1

    def once(self,warning):
        if warning not in self.uttered:
            if self.enabled: logger.write(self.pfx + warning)
            self.uttered[warning] = 1

    def __call__(self,warning):
        self.once(warning)

warnOnce=WarnOnce()
infoOnce=WarnOnce('Info')
