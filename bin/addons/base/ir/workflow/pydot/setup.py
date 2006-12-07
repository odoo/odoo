#!/usr/bin/env python

from distutils.core import setup
import pydot

setup(	name = 'pydot',
	version = pydot.__version__,
	description = 'Python interface to Graphiz\'s Dot',
	author = 'Ero Carrera',
	author_email = 'ero@dkbza.org',
	url = 'http://dkbza.org/pydot.html',
	license = 'MIT',
	platforms = ["any"],
	classifiers =	['Development Status :: 5 - Production/Stable',	\
			 'Intended Audience :: Science/Research',	\
			 'License :: OSI Approved :: MIT License',\
			 'Natural Language :: English',			\
			 'Operating System :: OS Independent',		\
			 'Programming Language :: Python',		\
			 'Topic :: Scientific/Engineering :: Visualization',\
			 'Topic :: Software Development :: Libraries :: Python Modules'],
	long_description = "\n".join(pydot.__doc__.split('\n')),
	py_modules = ['pydot', 'dot_parser'])
