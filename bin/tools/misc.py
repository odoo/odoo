# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################

"""
Miscelleanous tools used by tiny ERP.
"""

import os, time, sys
import inspect

import psycopg
#import netsvc
from config import config
#import tools

import zipfile
import release
import socket

if sys.version_info[:2] < (2, 4):
    from threadinglocal import local
else:
    from threading import local

from itertools import izip

# initialize a database with base/base.sql 
def init_db(cr):
    import addons
    f = addons.get_module_resource('base', 'base.sql')
    for line in file(f).read().split(';'):
        if (len(line)>0) and (not line.isspace()):
            cr.execute(line)
    cr.commit()

    for i in addons.get_modules():
        terp_file = addons.get_module_resource(i, '__terp__.py')
        mod_path = addons.get_module_path(i)
        info = False
        if os.path.isfile(terp_file) and not os.path.isfile(mod_path+'.zip'):
            info = eval(file(terp_file).read())
        elif zipfile.is_zipfile(mod_path+'.zip'):
            zfile = zipfile.ZipFile(mod_path+'.zip')
            i = os.path.splitext(i)[0]
            info = eval(zfile.read(os.path.join(i, '__terp__.py')))
        if info:
            categs = info.get('category', 'Uncategorized').split('/')
            p_id = None
            while categs:
                if p_id is not None:
                    cr.execute('select id \
                            from ir_module_category \
                            where name=%s and parent_id=%d', (categs[0], p_id))
                else:
                    cr.execute('select id \
                            from ir_module_category \
                            where name=%s and parent_id is NULL', (categs[0],))
                c_id = cr.fetchone()
                if not c_id:
                    cr.execute('select nextval(\'ir_module_category_id_seq\')')
                    c_id = cr.fetchone()[0]
                    cr.execute('insert into ir_module_category \
                            (id, name, parent_id) \
                            values (%d, %s, %d)', (c_id, categs[0], p_id))
                else:
                    c_id = c_id[0]
                p_id = c_id
                categs = categs[1:]

            active = info.get('active', False)
            installable = info.get('installable', True)
            if installable:
                if active:
                    state = 'to install'
                else:
                    state = 'uninstalled'
            else:
                state = 'uninstallable'
            cr.execute('select nextval(\'ir_module_module_id_seq\')')
            id = cr.fetchone()[0]
            cr.execute('insert into ir_module_module \
                    (id, author, latest_version, website, name, shortdesc, description, \
                        category_id, state) \
                    values (%d, %s, %s, %s, %s, %s, %s, %d, %s)', (
                id, info.get('author', ''),
                release.version.rsplit('.', 1)[0] + '.' + info.get('version', ''),
                info.get('website', ''), i, info.get('name', False),
                info.get('description', ''), p_id, state))
            dependencies = info.get('depends', [])
            for d in dependencies:
                cr.execute('insert into ir_module_module_dependency \
                        (module_id,name) values (%s, %s)', (id, d))
            cr.commit()

def find_in_path(name):
    if os.name == "nt":
        sep = ';'
    else:
        sep = ':'
    path = [dir for dir in os.environ['PATH'].split(sep)
            if os.path.isdir(dir)]
    for dir in path:
        val = os.path.join(dir, name)
        if os.path.isfile(val) or os.path.islink(val):
            return val
    return None

def find_pg_tool(name):
    if config['pg_path'] and config['pg_path'] != 'None':
        return os.path.join(config['pg_path'], name)
    else:
        return find_in_path(name)

def exec_pg_command(name, *args):
    prog = find_pg_tool(name)
    if not prog:
        raise Exception('Couldn\'t find %s' % name)
    args2 = (os.path.basename(prog),) + args
    return os.spawnv(os.P_WAIT, prog, args2)

def exec_pg_command_pipe(name, *args):
    prog = find_pg_tool(name)
    if not prog:
        raise Exception('Couldn\'t find %s' % name)
    if os.name == "nt":
        cmd = '"' + prog + '" ' + ' '.join(args)
    else:
        cmd = prog + ' ' + ' '.join(args)
    return os.popen2(cmd, 'b')

def exec_command_pipe(name, *args):
    prog = find_in_path(name)
    if not prog:
        raise Exception('Couldn\'t find %s' % name)
    if os.name == "nt":
        cmd = '"'+prog+'" '+' '.join(args)
    else:
        cmd = prog+' '+' '.join(args)
    return os.popen2(cmd, 'b')

#----------------------------------------------------------
# File paths
#----------------------------------------------------------
#file_path_root = os.getcwd()
#file_path_addons = os.path.join(file_path_root, 'addons')

def file_open(name, mode="r", subdir='addons', pathinfo=False):
    """Open a file from the Tiny ERP root, using a subdir folder.

    >>> file_open('hr/report/timesheer.xsl')
    >>> file_open('addons/hr/report/timesheet.xsl')
    >>> file_open('../../base/report/rml_template.xsl', subdir='addons/hr/report', pathinfo=True)

    @param name: name of the file
    @param mode: file open mode
    @param subdir: subdirectory
    @param pathinfo: if True returns tupple (fileobject, filepath)

    @return: fileobject if pathinfo is False else (fileobject, filepath)
    """

    adp = os.path.normcase(os.path.abspath(config['addons_path']))
    rtp = os.path.normcase(os.path.abspath(config['root_path']))

    if name.replace(os.path.sep, '/').startswith('addons/'):
        subdir = 'addons'
        name = name[7:]

    # First try to locate in addons_path
    if subdir:
        subdir2 = subdir
        if subdir2.replace(os.path.sep, '/').startswith('addons/'):
            subdir2 = subdir2[7:]

        subdir2 = (subdir2 != 'addons' or None) and subdir2

        try:
            if subdir2:
                fn = os.path.join(adp, subdir2, name)
            else:
                fn = os.path.join(adp, name)
            fn = os.path.normpath(fn)
            fo = file_open(fn, mode=mode, subdir=None, pathinfo=pathinfo)
            if pathinfo:
                return fo, fn
            return fo
        except IOError, e:
            pass

    if subdir:
        name = os.path.join(rtp, subdir, name)
    else:
        name = os.path.join(rtp, name)

    name = os.path.normpath(name)

    # Check for a zipfile in the path
    head = name
    zipname = False
    name2 = False
    while True:
        head, tail = os.path.split(head)
        if not tail:
            break
        if zipname:
            zipname = os.path.join(tail, zipname)
        else:
            zipname = tail
        if zipfile.is_zipfile(head+'.zip'):
            import StringIO
            zfile = zipfile.ZipFile(head+'.zip')
            try:
                fo = StringIO.StringIO(zfile.read(os.path.join(
                    os.path.basename(head), zipname).replace(
                        os.sep, '/')))

                if pathinfo:
                    return fo, name
                return fo
            except:
                name2 = os.path.normpath(os.path.join(head + '.zip', zipname))
                pass
    for i in (name2, name):
        if i and os.path.isfile(i):
            fo = file(i, mode)
            if pathinfo:
                return fo, i
            return fo

    raise IOError, 'File not found : '+str(name)


#----------------------------------------------------------
# iterables
#----------------------------------------------------------
def flatten(list):
    """Flatten a list of elements into a uniqu list
    Author: Christophe Simonis (christophe@tinyerp.com)
    
    Examples:
    >>> flatten(['a'])
    ['a']
    >>> flatten('b')
    ['b']
    >>> flatten( [] )
    []
    >>> flatten( [[], [[]]] )
    []
    >>> flatten( [[['a','b'], 'c'], 'd', ['e', [], 'f']] )
    ['a', 'b', 'c', 'd', 'e', 'f']
    >>> t = (1,2,(3,), [4, 5, [6, [7], (8, 9), ([10, 11, (12, 13)]), [14, [], (15,)], []]])
    >>> flatten(t)
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    """
    
    def isiterable(x):
        return hasattr(x, "__iter__")

    r = []
    for e in list:
        if isiterable(e):
            map(r.append, flatten(e))
        else:
            r.append(e)
    return r

reverse_enumerate = lambda l: izip(xrange(len(l)-1, -1, -1), reversed(l))
reverse_enumerate.__doc__ = \
"""Like enumerate but in the other sens
>>> a = ['a', 'b', 'c']
>>> it = reverse_enumerate(a)
>>> it.next()
(2, 'c')
>>> it.next()
(1, 'b')
>>> it.next()
(0, 'a')
>>> it.next()
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
StopIteration
"""

#----------------------------------------------------------
# Emails
#----------------------------------------------------------
def email_send(email_from, email_to, subject, body, email_cc=None, email_bcc=None, on_error=False, reply_to=False, tinycrm=False):
    """Send an email."""
    if not email_cc:
        email_cc=[]
    if not email_bcc:
        email_bcc=[]
    import smtplib
    from email.MIMEText import MIMEText
    from email.MIMEMultipart import MIMEMultipart
    from email.Header import Header
    from email.Utils import formatdate, COMMASPACE

    msg = MIMEText(body or '', _charset='utf-8')
    msg['Subject'] = Header(subject.decode('utf8'), 'utf-8')
    msg['From'] = email_from
    del msg['Reply-To']
    if reply_to:
        msg['Reply-To'] = msg['From']+', '+reply_to
    msg['To'] = COMMASPACE.join(email_to)
    if email_cc:
        msg['Cc'] = COMMASPACE.join(email_cc)
    if email_bcc:
        msg['Bcc'] = COMMASPACE.join(email_bcc)
    msg['Date'] = formatdate(localtime=True)
    if tinycrm:
        msg['Message-Id'] = '<'+str(time.time())+'-tinycrm-'+str(tinycrm)+'@'+socket.gethostname()+'>'
    try:
        s = smtplib.SMTP()
        s.connect(config['smtp_server'])
        if config['smtp_user'] or config['smtp_password']:
            s.login(config['smtp_user'], config['smtp_password'])
        s.sendmail(email_from, flatten([email_to, email_cc, email_bcc]), msg.as_string())
        s.quit()
    except Exception, e:
        import logging
        logging.getLogger().error(str(e))
    return True


#----------------------------------------------------------
# Emails
#----------------------------------------------------------
def email_send_attach(email_from, email_to, subject, body, email_cc=None, email_bcc=None, on_error=False, reply_to=False, attach=None, tinycrm=False, ssl=False, debug=False):
    """Send an email."""
    if not email_cc:
        email_cc=[]
    if not email_bcc:
        email_bcc=[]
    if not attach:
        attach=[]
    import smtplib
    from email.MIMEText import MIMEText
    from email.MIMEBase import MIMEBase
    from email.MIMEMultipart import MIMEMultipart
    from email.Header import Header
    from email.Utils import formatdate, COMMASPACE
    from email import Encoders

    msg = MIMEMultipart()
    
    if not ssl:
        ssl = config['smtp_ssl']
        
    msg['Subject'] = Header(subject.decode('utf8'), 'utf-8')
    msg['From'] = email_from
    del msg['Reply-To']
    if reply_to:
        msg['Reply-To'] = reply_to
    msg['To'] = COMMASPACE.join(email_to)
    if email_cc:
        msg['Cc'] = COMMASPACE.join(email_cc)
    if email_bcc:
        msg['Bcc'] = COMMASPACE.join(email_bcc)
    if tinycrm:
        msg['Message-Id'] = '<'+str(time.time())+'-tinycrm-'+str(tinycrm)+'@'+socket.gethostname()+'>'
    msg['Date'] = formatdate(localtime=True)
    msg.attach( MIMEText(body or '', _charset='utf-8') )
    for (fname,fcontent) in attach:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( fcontent )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % (fname,))
        msg.attach(part)
    try:
        s = smtplib.SMTP()
	
        if debug:
            s.debuglevel = 5		
        if ssl:
            s.ehlo()
            s.starttls()
            s.ehlo()
      
        s.connect(config['smtp_server'])
        if config['smtp_user'] or config['smtp_password']:
            s.login(config['smtp_user'], config['smtp_password'])
        s.sendmail(email_from, flatten([email_to, email_cc, email_bcc]), msg.as_string())
        s.quit()
    except Exception, e:
        import logging
        logging.getLogger().error(str(e))
        return False

    return True

#----------------------------------------------------------
# SMS
#----------------------------------------------------------
# text must be latin-1 encoded
def sms_send(user, password, api_id, text, to):
    import urllib
    params = urllib.urlencode({'user': user, 'password': password, 'api_id': api_id, 'text': text, 'to':to})
    #f = urllib.urlopen("http://api.clickatell.com/http/sendmsg", params)
    f = urllib.urlopen("http://196.7.150.220/http/sendmsg", params)
    print f.read()
    return True

#---------------------------------------------------------
# Class that stores an updateable string (used in wizards)
#---------------------------------------------------------
class UpdateableStr(local):

    def __init__(self, string=''):
        self.string = string
    
    def __str__(self):
        return str(self.string)

    def __repr__(self):
        return str(self.string)

    def __nonzero__(self):
        return bool(self.string)


class UpdateableDict(local):
    '''Stores an updateable dict to use in wizards'''

    def __init__(self, dict=None):
        if dict is None:
            dict = {}
        self.dict = dict

    def __str__(self):
        return str(self.dict)

    def __repr__(self):
        return str(self.dict)

    def clear(self):
        return self.dict.clear()

    def keys(self):
        return self.dict.keys()

    def __setitem__(self, i, y):
        self.dict.__setitem__(i, y)

    def __getitem__(self, i):
        return self.dict.__getitem__(i)

    def copy(self):
        return self.dict.copy()

    def iteritems(self):
        return self.dict.iteritems()

    def iterkeys(self):
        return self.dict.iterkeys()

    def itervalues(self):
        return self.dict.itervalues()

    def pop(self, k, d=None):
        return self.dict.pop(k, d)

    def popitem(self):
        return self.dict.popitem()

    def setdefault(self, k, d=None):
        return self.dict.setdefault(k, d)

    def update(self, E, **F):
        return self.dict.update(E, F)

    def values(self):
        return self.dict.values()

    def get(self, k, d=None):
        return self.dict.get(k, d)

    def has_key(self, k):
        return self.dict.has_key(k)

    def items(self):
        return self.dict.items()

    def __cmp__(self, y):
        return self.dict.__cmp__(y)

    def __contains__(self, k):
        return self.dict.__contains__(k)

    def __delitem__(self, y):
        return self.dict.__delitem__(y)

    def __eq__(self, y):
        return self.dict.__eq__(y)

    def __ge__(self, y):
        return self.dict.__ge__(y)

    def __getitem__(self, y):
        return self.dict.__getitem__(y)

    def __gt__(self, y):
        return self.dict.__gt__(y)

    def __hash__(self):
        return self.dict.__hash__()

    def __iter__(self):
        return self.dict.__iter__()

    def __le__(self, y):
        return self.dict.__le__(y)

    def __len__(self):
        return self.dict.__len__()

    def __lt__(self, y):
        return self.dict.__lt__(y)

    def __ne__(self, y):
        return self.dict.__ne__(y)


# Don't use ! Use res.currency.round()
class currency(float):

    def __init__(self, value, accuracy=2, rounding=None):
        if rounding is None:
            rounding=10**-accuracy
        self.rounding=rounding
        self.accuracy=accuracy

    def __new__(cls, value, accuracy=2, rounding=None):
        return float.__new__(cls, round(value, accuracy))

    #def __str__(self):
    #   display_value = int(self*(10**(-self.accuracy))/self.rounding)*self.rounding/(10**(-self.accuracy))
    #   return str(display_value)


#
# Use it as a decorator of the function you plan to cache
# Timeout: 0 = no timeout, otherwise in seconds
#
class cache(object):
    def __init__(self, timeout=10000, skiparg=2):
        self.timeout = timeout
        self.cache = {}

    def __call__(self, fn):
        arg_names = inspect.getargspec(fn)[0][2:]
        def cached_result(self2, cr=None, *args, **kwargs):
            if cr is None:
                self.cache = {}
                return True

            # Update named arguments with positional argument values
            kwargs.update(dict(zip(arg_names, args)))
            kwargs = kwargs.items()
            kwargs.sort()
            
            # Work out key as a tuple of ('argname', value) pairs
            key = (('dbname', cr.dbname),) + tuple(kwargs)

            # Check cache and return cached value if possible
            if key in self.cache:
                (value, last_time) = self.cache[key]
                mintime = time.time() - self.timeout
                if self.timeout <= 0 or mintime <= last_time:
                    return value

            # Work out new value, cache it and return it
            # Should copy() this value to avoid futur modf of the cacle ?
            result = fn(self2,cr,**dict(kwargs))

            self.cache[key] = (result, time.time())
            return result
        return cached_result

def to_xml(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def get_languages():
    languages={
        'zh_CN': 'Chinese (CN)',
        'zh_TW': 'Chinese (TW)',
        'cs_CZ': 'Czech',
        'de_DE': 'Deutsch',
        'es_AR': 'Español (Argentina)',
        'es_ES': 'Español (España)',
        'fr_FR': 'Français',
        'fr_CH': 'Français (Suisse)',
        'en_EN': 'English (default)',
        'hu_HU': 'Hungarian',
        'it_IT': 'Italiano',
        'pt_BR': 'Portugese (Brasil)',
        'pt_PT': 'Portugese (Portugal)',
        'nl_NL': 'Nederlands',
        'ro_RO': 'Romanian',
        'ru_RU': 'Russian',
        'sv_SE': 'Swedish',
    }
    return languages

def scan_languages():
    import glob
    file_list = [os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(config['root_path'], 'i18n', '*.csv'))]
    lang_dict = get_languages()
    return [(lang, lang_dict.get(lang, lang)) for lang in file_list]


def get_user_companies(cr, user):
    def _get_company_children(cr, ids):
        if not ids:
            return []
        cr.execute('SELECT id FROM res_company WHERE parent_id = any(array[%s])' %(','.join([str(x) for x in ids]),))
        res=[x[0] for x in cr.fetchall()]
        res.extend(_get_company_children(cr, res))
        return res
    cr.execute('SELECT comp.id FROM res_company AS comp, res_users AS u WHERE u.id = %d AND comp.id = u.company_id' % (user,))
    compids=[cr.fetchone()[0]]
    compids.extend(_get_company_children(cr, compids))
    return compids

def mod10r(number):
    """
    Input number : account or invoice number
    Output return: the same number completed with the recursive mod10
    key
    """
    codec=[0,9,4,6,8,2,7,1,3,5]
    report = 0
    result=""
    for digit in number:
        result += digit
        if digit.isdigit():
            report = codec[ (int(digit) + report) % 10 ]
    return result + str((10 - report) % 10)




if __name__ == '__main__':
    import doctest
    doctest.testmod()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

