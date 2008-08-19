* What is this package?

PyChart is a Python library for creating professional quality PS, PDF,
PNG, or SVG charts.  It supports line plots, bar plots, range-fill
plots, and pie charts.  Because it is based on Python, you can make
the full use of Python's scripting power.

The PyChart home page is at 
http://www.hpl.hp.com/personal/Yasushi_Saito/pychart

* What you need

You need Python (http://www.python.org) version 2.2 or later (on
Debian GNU/Linux, you need, python-xml package as well). You also need
Ghostscript (http://www.cs.wisc.edu/~ghost/) to produce PNG
files. 

	Pychart used to require Ghostscript during PS and PDF
	generation to obtain font metric information, but that's no
	longer the case.

* Platforms supported

In theory, PyChart works on any platform with Python.  In practice,
I've run PyChart on Linux and Win2000.

* Installation

Become a root and do:

	# python setup.py install

Or, you can set PYTHONPATH environment variable before you start
Python. For example (in bash):

% PYTHONPATH=~/PyChart-1.33/pychart python mumbo.py

* Documentation

A detailed documentation is found in doc/pychart.

* Examples

All the *.py files in the demos/ directory can be run directly. For
example,

    setenv PYTHONPATH ..
    python linetest.py >foo.eps
    gs foo.eps

or

    setenv PYTHONPATH ..
    setenv PYCHART_OPTIONS="format=pdf"
    python linetest.py >foo.pdf
    acroread foo.pdf

* About the author

Yasushi Saito (ysaito@hpl.hp.com), a full-time researcher and
part-time hacker. This program is created mainly to serve my personal
needs to write pretty charts for research papers. As such, it is
updated only when I'm writing a paper, which happens about once every
half year or so.

Anyway, if you have comments, requests, or (even better)
fixes/enhancements, feel free to email me.

