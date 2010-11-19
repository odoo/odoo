# This module is part of the spambayes project, which is Copyright 2003
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import sys
import win32api, win32con
import win32com.client
import pythoncom

try:
    True, False
except NameError:
    # Maintain compatibility with Python 2.2
    True, False = 1, 0

try:
    filesystem_encoding = sys.getfilesystemencoding()
except AttributeError:
    filesystem_encoding = "mbcs"

# Work out our "application directory", which is
# the directory of our main .py/.dll/.exe file we
# are running from.
if hasattr(sys, "frozen"):
    assert sys.frozen == "dll", "outlook only supports inproc servers"
    this_filename = win32api.GetModuleFileName(sys.frozendllhandle)
else:
    try:
        this_filename = os.path.abspath(__file__)
    except NameError: # no __file__ - means Py2.2 and __name__=='__main__'
        this_filename = os.path.abspath(sys.argv[0])
# See if we can use the new bsddb module. (The old one is unreliable
# on Windows, so we don't use that)
try:
    import bsddb3 as bsddb
    # bsddb3 is definitely not broken
    use_db = True
except ImportError:
    # Not using the 3rd party bsddb3, so try the one in the std library
    try:
        import bsddb
        use_db = hasattr(bsddb, "db") # This name is not in the old one.
    except ImportError:
        # No DB library at all!
        assert not hasattr(sys, "frozen"), \
               "Don't build binary versions without bsddb!"
        use_db = False

def ustr(value):
    """This method is similar to the builtin `str` method, except
    it will return Unicode string.

    @param value: the value to convert

    @rtype: unicode
    @return: unicode string
    """
    if isinstance(value, unicode):
        return value

    if hasattr(value, '__unicode__'):
        return unicode(value)
    if not isinstance(value, str):
        value = str(value)
    try: # first try utf-8
        return unicode(value, 'utf-8')
    except:
        pass

    try: # then extened iso-8858
        return unicode(value, 'iso-8859-15')
    except:
        pass
    filesystem_encoding = sys.getfilesystemencoding()
    d = unicode(value, filesystem_encoding)
    return d

class OpenERPManager:
    def __init__(self, config_base="default", outlook=None, verbose=0):
        self.outlook = outlook
        self.dialog_parser = None
        self.application_directory = os.path.dirname(this_filename)
        self.windows_data_directory = self.LocateDataDirectory()
        self.data_directory = self.windows_data_directory
        self.default_objects = [('Partners','res.partner',''),('Account Invoices','account.invoice',''), \
                                ('Products', 'product.product',''),('Sale Orders','sale.order',''), \
                               ('Leads','crm.lead','')]

        self.config=self.LoadConfig()

    def WorkerThreadStarting(self):
        pythoncom.CoInitialize()

    def WorkerThreadEnding(self):
        pythoncom.CoUninitialize()

    def LocateDataDirectory(self):
        # Locate the best directory for our data files.
        from win32com.shell import shell, shellcon
        try:
            appdata = shell.SHGetFolderPath(0,shellcon.CSIDL_APPDATA,0,0)
            path = os.path.join(appdata, "OpenERP-Plugin")
            if not os.path.isdir(path):
                os.makedirs(path)
            return path
        except pythoncom.com_error:
            # Function doesn't exist on early win95,
            # and it may just fail anyway!
            return self.application_directory
        except EnvironmentError:
            # Can't make the directory.
            return self.application_directory

    def ShowManager(self, id="IDD_MANAGER"):
        import dialogs
        dialogs.ShowDialog(0, self, self.config, id)

    def LoadConfig(self):
        import win32ui
        path = os.path.join(self.data_directory, 'tiny.ini')
        data = {'server' : 'localhost', 'port' : '8069', 'protocol' : 'http://', 'database' : '', 'objects' : self.default_objects, 'uname':'admin', 'pwd':'a', 'login':False}
        if os.path.exists(path):
            fp = open(path, 'r')
            data = fp.readlines()
            try:
                data = eval(data[0])
                return data
            except e:
                return data
        else:
            return data

    def SaveConfig(self):
        path = os.path.join(self.data_directory, 'tiny.ini')
        fp = open(path, 'w')
        fp.write(str(self.config))
        fp.close()
_mgr = None

def GetManager(outlook = None):
    global _mgr
    if _mgr is None:
        if outlook is None:
            outlook = win32com.client.Dispatch("Outlook.Application")
        _mgr = OpenERPManager(outlook=outlook)
    return _mgr

def ShowManager(mgr):
    mgr.c()

def main(verbose_level = 1):
    mgr = GetManager()
    ShowManager(mgr)
    return 0

def usage():
    print "Usage: manager [-v ...]"
    sys.exit(1)

if __name__=='__main__':
    verbose = 1
    import getopt
    opts, args = getopt.getopt(sys.argv[1:], "v")
    if args:
        usage()
    for opt, val in opts:
        if opt=="-v":
            verbose += 1
        else:
            usage()
    sys.exit(main(verbose))
