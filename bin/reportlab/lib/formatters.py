#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/lib/formatters.py
__version__=''' $Id: formatters.py 2385 2004-06-17 15:26:05Z rgbecker $ '''
__doc__="""
These help format numbers and dates in a user friendly way.

Used by the graphics framework.
"""
import string, sys, os

class Formatter:
    "Base formatter - simply applies python format strings"
    def __init__(self, pattern):
        self.pattern = pattern
    def format(self, obj):
        return self.pattern % obj
    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self.pattern)
    def __call__(self, x):
        return self.format(x)


class DecimalFormatter(Formatter):
    """lets you specify how to build a decimal.

    A future NumberFormatter class will take Microsoft-style patterns
    instead - "$#,##0.00" is WAY easier than this."""
    def __init__(self, places=2, decimalSep='.', thousandSep=None, prefix=None, suffix=None):
        self.places = places
        self.dot = decimalSep
        self.comma = thousandSep
        self.prefix = prefix
        self.suffix = suffix

    def format(self, num):
        # positivize the numbers
        sign=num<0
        if sign:
            num = -num
        places, sep = self.places, self.dot
        strip = places<=0
        if places and strip: places = -places
        strInt = ('%.' + str(places) + 'f') % num
        if places:
            strInt, strFrac = strInt.split('.')
            strFrac = sep + strFrac
            if strip:
                while strFrac and strFrac[-1] in ['0',sep]: strFrac = strFrac[:-1]
        else:
            strFrac = ''

        if self.comma is not None:
            strNew = ''
            while strInt:
                left, right = strInt[0:-3], strInt[-3:]
                if left == '':
                    #strNew = self.comma + right + strNew
                    strNew = right + strNew
                else:
                    strNew = self.comma + right + strNew
                strInt = left
            strInt = strNew

        strBody = strInt + strFrac
        if sign: strBody = '-' + strBody
        if self.prefix:
            strBody = self.prefix + strBody
        if self.suffix:
            strBody = strBody + self.suffix
        return strBody

    def __repr__(self):
        return "%s(places=%d, decimalSep=%s, thousandSep=%s, prefix=%s, suffix=%s)" % (
                    self.__class__.__name__,
                    self.places,
                    repr(self.dot),
                    repr(self.comma),
                    repr(self.prefix),
                    repr(self.suffix)
                    )

if __name__=='__main__':
    def t(n, s, places=2, decimalSep='.', thousandSep=None, prefix=None, suffix=None):
        f=DecimalFormatter(places,decimalSep,thousandSep,prefix,suffix)
        r = f(n)
        print "places=%2d dot=%-4s comma=%-4s prefix=%-4s suffix=%-4s result=%10s %s" %(f.places, f.dot, f.comma, f.prefix, f.suffix,r, r==s and 'OK' or 'BAD')
    t(1000.9,'1,000.9',1,thousandSep=',')
    t(1000.95,'1,001.0',1,thousandSep=',')
    t(1000.95,'1,001',-1,thousandSep=',')
    t(1000.9,'1,001',0,thousandSep=',')
    t(1000.9,'1000.9',1)
    t(1000.95,'1001.0',1)
    t(1000.95,'1001',-1)
    t(1000.9,'1001',0)
    t(1000.1,'1000.1',1)
    t(1000.55,'1000.6',1)
    t(1000.449,'1000.4',-1)
    t(1000.45,'1000',0)