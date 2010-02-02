#!/usr/bin/env python

"""

    python davserver
    Copyright (C) 1999 Christian Scholz (ruebe@aachen.heimat.de)

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Library General Public
    License as published by the Free Software Foundation; either
    version 2 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Library General Public License for more details.

    You should have received a copy of the GNU Library General Public
    License along with this library; if not, write to the Free
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


"""
import os
import string
import urllib
from StringIO import StringIO

from status import STATUS_CODES
from utils import gen_estring, quote_uri, make_xmlresponse
from davcmd import deltree

class DELETE:

    def __init__(self,uri,dataclass):
        self.__dataclass=dataclass
        self.__uri=uri

    def delcol(self):
        """ delete a collection """

        dc=self.__dataclass
        result=dc.deltree(self.__uri)

        if not len(result.items()):
            return None # everything ok

        # create the result element
        return make_xmlresponse(result)

    def delone(self):
        """ delete a resource """

        dc=self.__dataclass
        result=dc.delone(self.__uri)
        
        if not result: return None
        if not len(result.items()):
            return None # everything ok

        # create the result element
        return make_xmlresponse(result)

