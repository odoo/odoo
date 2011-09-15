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
import pooler
import sql_db

import os
import time
import errno

import netsvc
import urlparse

from DAV.constants import COLLECTION  #, OBJECT
from DAV.errors import DAV_Error, DAV_Forbidden, DAV_NotFound
from DAV.iface import dav_interface
import urllib

from DAV.davcmd import copyone, copytree, moveone, movetree, delone, deltree
from cache import memoize
from tools import misc

from webdav import mk_lock_response

try:
    from tools.dict_tools import dict_merge2
except ImportError:
    from document.dict_tools import dict_merge2

CACHE_SIZE=20000

#hack for urlparse: add webdav in the net protocols
urlparse.uses_netloc.append('webdav')
urlparse.uses_netloc.append('webdavs')

day_names = { 0: 'Mon', 1: 'Tue' , 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun' }
month_names = { 1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec' }

class DAV_NotFound2(DAV_NotFound):
    """404 exception, that accepts our list uris
    """
    def __init__(self, *args):
        if len(args) and isinstance(args[0], (tuple, list)):
            path = ''.join([ '/' + x for x in args[0]])
            args = (path, )
        DAV_NotFound.__init__(self, *args)


def _str2time(cre):
    """ Convert a string with time representation (from db) into time (float)
    """
    if not cre:
        return time.time()
    frac = 0.0
    if isinstance(cre, basestring) and '.' in cre:
        fdot = cre.find('.')
        frac = float(cre[fdot:])
        cre = cre[:fdot]
    return time.mktime(time.strptime(cre,'%Y-%m-%d %H:%M:%S')) + frac

class BoundStream2(object):
    """Wraps around a seekable buffer, reads a determined range of data
    
        Note that the supplied stream object MUST support a size() which
        should return its data length (in bytes).
    
        A variation of the class in websrv_lib.py
    """
    
    def __init__(self, stream, offset=None, length=None, chunk_size=None):
        self._stream = stream
        self._offset = offset or 0
        self._length = length or self._stream.size()
        self._rem_length = length
        assert length and isinstance(length, (int, long))
        assert length and length >= 0, length
        self._chunk_size = chunk_size
        if offset is not None:
            self._stream.seek(offset)

    def read(self, size=-1):
        if not self._stream:
            raise IOError(errno.EBADF, "read() without stream")
        
        if self._rem_length == 0:
            return ''
        elif self._rem_length < 0:
            raise EOFError()

        rsize = self._rem_length
        if size > 0 and size < rsize:
            rsize = size
        if self._chunk_size and self._chunk_size < rsize:
            rsize = self._chunk_size
        
        data = self._stream.read(rsize)
        self._rem_length -= len(data)

        return data

    def __len__(self):
        return self._length

    def tell(self):
        res = self._stream.tell()
        if self._offset:
            res -= self._offset
        return res

    def __iter__(self):
        return self

    def next(self):
        return self.read(65536)

    def seek(self, pos, whence=os.SEEK_SET):
        """ Seek, computing our limited range
        """
        if whence == os.SEEK_SET:
            if pos < 0 or pos > self._length:
                raise IOError(errno.EINVAL,"Cannot seek")
            self._stream.seek(pos - self._offset)
            self._rem_length = self._length - pos
        elif whence == os.SEEK_CUR:
            if pos > 0:
                if pos > self._rem_length:
                    raise IOError(errno.EINVAL,"Cannot seek past end")
                elif pos < 0:
                    oldpos = self.tell()
                    if oldpos + pos < 0:
                        raise IOError(errno.EINVAL,"Cannot seek before start")
                self._stream.seek(pos, os.SEEK_CUR)
                self._rem_length -= pos
        elif whence == os.SEEK_END:
            if pos > 0:
                raise IOError(errno.EINVAL,"Cannot seek past end")
            else:
                if self._length + pos < 0:
                    raise IOError(errno.EINVAL,"Cannot seek before start")
            newpos = self._offset + self._length + pos
            self._stream.seek(newpos, os.SEEK_SET)
            self._rem_length = 0 - pos

class openerp_dav_handler(dav_interface):
    """
    This class models a OpenERP interface for the DAV server
    """
    PROPS={'DAV:': dav_interface.PROPS['DAV:'],}

    M_NS={ "DAV:" : dav_interface.M_NS['DAV:'],}

    def __init__(self,  parent, verbose=False):
        self.db_name_list=[]
        self.parent = parent
        self.baseuri = parent.baseuri
        self.verbose = verbose

    def get_propnames(self, uri):
        props = self.PROPS
        self.parent.log_message('get propnames: %s' % uri)
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            if cr: cr.close()
            # TODO: maybe limit props for databases..?
            return props
        node = self.uri2object(cr, uid, pool, uri2)
        if node:
            props = dict_merge2(props, node.get_dav_props(cr))
        cr.close()
        return props

    def _try_function(self, funct, args, opname='run function', cr=None,
            default_exc=DAV_Forbidden):
        """ Try to run a function, and properly convert exceptions to DAV ones.

            @objname the name of the operation being performed
            @param cr if given, the cursor to close at exceptions
        """

        try:
            return funct(*args)
        except DAV_Error:
            if cr: cr.close()
            raise
        except NotImplementedError, e:
            if cr: cr.close()
            import traceback
            self.parent.log_error("Cannot %s: %s", opname, str(e))
            self.parent.log_message("Exc: %s",traceback.format_exc())
            # see par 9.3.1 of rfc
            raise DAV_Error(403, str(e) or 'Not supported at this path')
        except EnvironmentError, err:
            if cr: cr.close()
            import traceback
            self.parent.log_error("Cannot %s: %s", opname, err.strerror)
            self.parent.log_message("Exc: %s",traceback.format_exc())
            raise default_exc(err.strerror)
        except Exception, e:
            import traceback
            if cr: cr.close()
            self.parent.log_error("Cannot %s: %s", opname, str(e))
            self.parent.log_message("Exc: %s",traceback.format_exc())
            raise default_exc("Operation failed")

    def _get_dav_lockdiscovery(self, uri):
        """ We raise that so that the node API is used """
        raise DAV_NotFound

    def _get_dav_supportedlock(self, uri):
        """ We raise that so that the node API is used """
        raise DAV_NotFound

    def match_prop(self, uri, match, ns, propname):
        if self.M_NS.has_key(ns):
            return match == dav_interface.get_prop(self, uri, ns, propname)
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            if cr: cr.close()
            raise DAV_NotFound
        node = self.uri2object(cr, uid, pool, uri2)
        if not node:
            cr.close()
            raise DAV_NotFound
        res = node.match_dav_eprop(cr, match, ns, propname)
        cr.close()
        return res

    def prep_http_options(self, uri, opts):
        """see HttpOptions._prep_OPTIONS """
        self.parent.log_message('get options: %s' % uri)
        cr, uid, pool, dbname, uri2 = self.get_cr(uri, allow_last=True)

        if not dbname:
            if cr: cr.close()
            return opts
        node = self.uri2object(cr, uid, pool, uri2[:])

        if not node:
            if cr: cr.close()
            return opts
        else:
            if hasattr(node, 'http_options'):
                ret = opts.copy()
                for key, val in node.http_options.items():
                    if isinstance(val, basestring):
                        val = [val, ]
                    if key in ret:
                        ret[key] = ret[key][:]  # copy the orig. array
                    else:
                        ret[key] = []
                    ret[key].extend(val)

                self.parent.log_message('options: %s' % ret)
            else:
                ret = opts
            cr.close()
            return ret

    def reduce_useragent(self):
        ua = self.parent.headers.get('User-Agent', False)
        ctx = {}
        if ua:
            if 'iPhone' in ua:
                ctx['DAV-client'] = 'iPhone'
            elif 'Konqueror' in ua:
                ctx['DAV-client'] = 'GroupDAV'
        return ctx

    def get_prop(self, uri, ns, propname):
        """ return the value of a given property

            uri        -- uri of the object to get the property of
            ns        -- namespace of the property
            pname        -- name of the property
         """
        if self.M_NS.has_key(ns):
            try:
                # if it's not in the interface class, a "DAV:" property
                # may be at the node class. So shouldn't give up early.
                return dav_interface.get_prop(self, uri, ns, propname)
            except DAV_NotFound:
                pass
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            if cr: cr.close()
            raise DAV_NotFound
        try:
            node = self.uri2object(cr, uid, pool, uri2)
            if not node:
                raise DAV_NotFound
            res = node.get_dav_eprop(cr, ns, propname)
        finally:
            cr.close()
        return res

    def get_db(self, uri, rest_ret=False, allow_last=False):
        """Parse the uri and get the dbname and the rest.
           Db name should be the first component in the unix-like
           path supplied in uri.

           @param rest_ret Instead of the db_name, return (db_name, rest),
                where rest is the remaining path
           @param allow_last If the dbname is the last component in the
                path, allow it to be resolved. The default False value means
                we will not attempt to use the db, unless there is more
                path.

           @return db_name or (dbname, rest) depending on rest_ret,
                will return dbname=False when component is not found.
        """

        uri2 = self.uri2local(uri)
        if uri2.startswith('/'):
            uri2 = uri2[1:]
        names=uri2.split('/',1)
        db_name=False
        rest = None
        if allow_last:
            ll = 0
        else:
            ll = 1
        if len(names) > ll and names[0]:
            db_name = names[0]
            names = names[1:]

        if rest_ret:
            if len(names):
                rest = names[0]
            return db_name, rest
        return db_name


    def urijoin(self,*ajoin):
        """ Return the base URI of this request, or even join it with the
            ajoin path elements
        """
        return self.parent.get_baseuri(self) + '/'.join(ajoin)

    @memoize(4)
    def db_list(self):
        s = netsvc.ExportService.getService('db')
        result = s.exp_list()
        self.db_name_list=[]
        for db_name in result:
            cr = None
            try:
                db = sql_db.db_connect(db_name)
                cr = db.cursor()
                cr.execute("SELECT id FROM ir_module_module WHERE name = 'document' AND state='installed' ")
                res=cr.fetchone()
                if res and len(res):
                    self.db_name_list.append(db_name)
            except Exception, e:
                self.parent.log_error("Exception in db list: %s" % e)
            finally:
                if cr:
                    cr.close()
        return self.db_name_list

    def get_childs(self,uri, filters=None):
        """ return the child objects as self.baseuris for the given URI """
        self.parent.log_message('get children: %s' % uri)
        cr, uid, pool, dbname, uri2 = self.get_cr(uri, allow_last=True)

        if not dbname:
            if cr: cr.close()
            res = map(lambda x: self.urijoin(x), self.db_list())
            return res
        result = []
        node = self.uri2object(cr, uid, pool, uri2[:])

        try:
            if not node:
                raise DAV_NotFound2(uri2)
            else:
                fp = node.full_path()
                if fp and len(fp):
                    fp = '/'.join(fp)
                    self.parent.log_message('children for: %s' % fp)
                else:
                    fp = None
                domain = None
                if filters:
                    domain = node.get_domain(cr, filters)
                    
                    if hasattr(filters, 'getElementsByTagNameNS'):
                        hrefs = filters.getElementsByTagNameNS('DAV:', 'href')
                        if hrefs:
                            ul = self.parent.davpath + self.uri2local(uri)
                            for hr in hrefs:
                                turi = ''
                                for tx in hr.childNodes:
                                    if tx.nodeType == hr.TEXT_NODE:
                                        turi += tx.data
                                if not turi.startswith('/'):
                                    # it may be an absolute URL, decode to the
                                    # relative part, because ul is relative, anyway
                                    uparts=urlparse.urlparse(turi)
                                    turi=uparts[2]
                                    if uparts[3]:
                                        turi += ';' + uparts[3]
                                if turi.startswith(ul):
                                    result.append( turi[len(self.parent.davpath):])
                                else:
                                    self.parent.log_error("ignore href %s because it is not under request path %s", turi, ul)
                            return result
                            # We don't want to continue with the children found below
                            # Note the exceptions and that 'finally' will close the
                            # cursor
                for d in node.children(cr, domain):
                    self.parent.log_message('child: %s' % d.path)
                    if fp:
                        result.append( self.urijoin(dbname,fp,d.path) )
                    else:
                        result.append( self.urijoin(dbname,d.path) )
        except DAV_Error:
            raise
        except Exception, e:
            self.parent.log_error("cannot get_children: "+ str(e))
            raise
        finally:
            if cr: cr.close()
        return result

    def uri2local(self, uri):
        uparts=urlparse.urlparse(uri)
        reluri=uparts[2]
        if uparts[3]:
            reluri += ';'+uparts[3]
        if reluri and reluri[-1]=="/":
            reluri=reluri[:-1]
        return reluri

    #
    # pos: -1 to get the parent of the uri
    #
    def get_cr(self, uri, allow_last=False):
        """ Split the uri, grab a cursor for that db
        """
        pdb = self.parent.auth_proxy.last_auth
        dbname, uri2 = self.get_db(uri, rest_ret=True, allow_last=allow_last)
        uri2 = (uri2 and uri2.split('/')) or []
        if not dbname:
            return None, None, None, False, uri2
        # if dbname was in our uri, we should have authenticated
        # against that.
        assert pdb == dbname, " %s != %s" %(pdb, dbname)
        res = self.parent.auth_proxy.auth_creds.get(dbname, False)
        if not res:
            self.parent.auth_proxy.checkRequest(self.parent, uri, dbname)
            res = self.parent.auth_proxy.auth_creds[dbname]
        user, passwd, dbn2, uid = res
        db,pool = pooler.get_db_and_pool(dbname)
        cr = db.cursor()
        return cr, uid, pool, dbname, uri2

    def uri2object(self, cr, uid, pool, uri):
        if not uid:
            return None
        context = self.reduce_useragent()
        return pool.get('document.directory').get_object(cr, uid, uri, context=context)

    def get_data(self,uri, rrange=None):
        self.parent.log_message('GET: %s' % uri)
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        try:
            if not dbname:
                raise DAV_Error, 409
            node = self.uri2object(cr, uid, pool, uri2)
            if not node:
                raise DAV_NotFound2(uri2)
            # TODO: if node is a collection, for some specific set of
            # clients ( web browsers; available in node context), 
            # we may return a pseydo-html page with the directory listing.
            try:
                res = node.open_data(cr,'r')
                if rrange:
                    assert isinstance(rrange, (tuple,list))
                    start, end = map(long, rrange)
                    if not start:
                        start = 0
                    assert start >= 0
                    if end and end < start:
                        self.parent.log_error("Invalid range for data: %s-%s" %(start, end))
                        raise DAV_Error(416, "Invalid range for data")
                    if end:
                        if end >= res.size():
                            raise DAV_Error(416, "Requested data exceeds available size")
                        length = (end + 1) - start
                    else:
                        length = res.size() - start
                    res = BoundStream2(res, offset=start, length=length)
                
            except TypeError,e:
                # for the collections that return this error, the DAV standard
                # says we'd better just return 200 OK with empty data
                return ''
            except IndexError,e :
                self.parent.log_error("GET IndexError: %s", str(e))
                raise DAV_NotFound2(uri2)
            except Exception,e:
                import traceback
                self.parent.log_error("GET exception: %s",str(e))
                self.parent.log_message("Exc: %s", traceback.format_exc())
                raise DAV_Error, 409
            return res
        finally:
            if cr: cr.close()

    @memoize(CACHE_SIZE)
    def _get_dav_resourcetype(self, uri):
        """ return type of object """
        self.parent.log_message('get RT: %s' % uri)
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        try:
            if not dbname:
                return COLLECTION
            node = self.uri2object(cr, uid, pool, uri2)
            if not node:
                raise DAV_NotFound2(uri2)
            try:
                return node.get_dav_resourcetype(cr)
            except NotImplementedError:
                if node.type in ('collection','database'):
                    return ('collection', 'DAV:')
                return ''
        finally:
            if cr: cr.close()

    def _get_dav_displayname(self,uri):
        self.parent.log_message('get DN: %s' % uri)
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            if cr: cr.close()
            # at root, dbname, just return the last component
            # of the path.
            if uri2 and len(uri2) < 2:
                return uri2[-1]
            return ''
        node = self.uri2object(cr, uid, pool, uri2)
        if not node:
            if cr: cr.close()
            raise DAV_NotFound2(uri2)
        cr.close()
        return node.displayname

    @memoize(CACHE_SIZE)
    def _get_dav_getcontentlength(self, uri):
        """ return the content length of an object """        
        self.parent.log_message('get length: %s' % uri)
        result = 0
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)        
        if not dbname:
            if cr: cr.close()
            return str(result)
        node = self.uri2object(cr, uid, pool, uri2)
        if not node:
            if cr: cr.close()
            raise DAV_NotFound2(uri2)
        result = node.content_length or 0
        cr.close()
        return str(result)

    @memoize(CACHE_SIZE)
    def _get_dav_getetag(self,uri):
        """ return the ETag of an object """
        self.parent.log_message('get etag: %s' % uri)
        result = 0
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            if cr: cr.close()
            return '0'
        node = self.uri2object(cr, uid, pool, uri2)
        if not node:
            cr.close()
            raise DAV_NotFound2(uri2)
        result = self._try_function(node.get_etag ,(cr,), "etag %s" %uri, cr=cr)
        cr.close()
        return str(result)

    @memoize(CACHE_SIZE)
    def get_lastmodified(self, uri):
        """ return the last modified date of the object """
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            return time.time()
        try:            
            node = self.uri2object(cr, uid, pool, uri2)
            if not node:
                raise DAV_NotFound2(uri2)
            return _str2time(node.write_date)
        finally:
            if cr: cr.close()

    def _get_dav_getlastmodified(self,uri):
        """ return the last modified date of a resource
        """
        d=self.get_lastmodified(uri)
        # format it. Note that we explicitly set the day, month names from
        # an array, so that strftime() doesn't use its own locale-aware
        # strings.
        gmt = time.gmtime(d)
        return time.strftime("%%s, %d %%s %Y %H:%M:%S GMT", gmt ) % \
                    (day_names[gmt.tm_wday], month_names[gmt.tm_mon])

    @memoize(CACHE_SIZE)
    def get_creationdate(self, uri):
        """ return the last modified date of the object """        
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            raise DAV_Error, 409
        try:            
            node = self.uri2object(cr, uid, pool, uri2)
            if not node:
                raise DAV_NotFound2(uri2)

            return _str2time(node.create_date)
        finally:
            if cr: cr.close()

    @memoize(CACHE_SIZE)
    def _get_dav_getcontenttype(self,uri):
        self.parent.log_message('get contenttype: %s' % uri)
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            if cr: cr.close()
            return 'httpd/unix-directory'
        try:            
            node = self.uri2object(cr, uid, pool, uri2)
            if not node:
                raise DAV_NotFound2(uri2)
            result = str(node.mimetype)
            return result
            #raise DAV_NotFound, 'Could not find %s' % path
        finally:
            if cr: cr.close()    
    
    def mkcol(self,uri):
        """ create a new collection
            see par. 9.3 of rfc4918
        """
        self.parent.log_message('MKCOL: %s' % uri)
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not uri2[-1]:
            if cr: cr.close()
            raise DAV_Error(409, "Cannot create nameless collection")
        if not dbname:
            if cr: cr.close()
            raise DAV_Error, 409
        node = self.uri2object(cr,uid,pool, uri2[:-1])
        if not node:
            cr.close()
            raise DAV_Error(409, "Parent path %s does not exist" % uri2[:-1])
        nc = node.child(cr, uri2[-1])
        if nc:
            cr.close()
            raise DAV_Error(405, "Path already exists")
        self._try_function(node.create_child_collection, (cr, uri2[-1]),
                    "create col %s" % uri2[-1], cr=cr)
        cr.commit()
        cr.close()
        return True

    def put(self, uri, data, content_type=None):
        """ put the object into the filesystem """
        self.parent.log_message('Putting %s (%d), %s'%( misc.ustr(uri), data and len(data) or 0, content_type))
        cr, uid, pool,dbname, uri2 = self.get_cr(uri)
        if not dbname:
            if cr: cr.close()
            raise DAV_Forbidden
        try:
            node = self.uri2object(cr, uid, pool, uri2[:])
        except Exception:
            node = False
        
        objname = misc.ustr(uri2[-1])
        
        ret = None
        if not node:
            dir_node = self.uri2object(cr, uid, pool, uri2[:-1])
            if not dir_node:
                cr.close()
                raise DAV_NotFound('Parent folder not found')

            newchild = self._try_function(dir_node.create_child, (cr, objname, data),
                    "create %s" % objname, cr=cr)
            if not newchild:
                cr.commit()
                cr.close()
                raise DAV_Error(400, "Failed to create resource")
            
            uparts=urlparse.urlparse(uri)
            fileloc = '/'.join(newchild.full_path())
            if isinstance(fileloc, unicode):
                fileloc = fileloc.encode('utf-8')
            # the uri we get is a mangled one, where the davpath has been removed
            davpath = self.parent.get_davpath()
            
            surl = '%s://%s' % (uparts[0], uparts[1])
            uloc = urllib.quote(fileloc)
            hurl = False
            if uri != ('/'+uloc) and uri != (surl + '/' + uloc):
                hurl = '%s%s/%s/%s' %(surl, davpath, dbname, uloc)
            etag = False
            try:
                etag = str(newchild.get_etag(cr))
            except Exception, e:
                self.parent.log_error("Cannot get etag for node: %s" % e)
            ret = (str(hurl), etag)
        else:
            self._try_function(node.set_data, (cr, data), "save %s" % objname, cr=cr)
            
        cr.commit()
        cr.close()
        return ret

    def rmcol(self,uri):
        """ delete a collection """
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)        
        if not dbname:
            if cr: cr.close()
            raise DAV_Error, 409

        node = self.uri2object(cr, uid, pool, uri2)             
        self._try_function(node.rmcol, (cr,), "rmcol %s" % uri, cr=cr)

        cr.commit()
        cr.close()
        return 204

    def rm(self,uri):
        cr, uid, pool,dbname, uri2 = self.get_cr(uri)
        if not dbname:        
            if cr: cr.close()
            raise DAV_Error, 409
        node = self.uri2object(cr, uid, pool, uri2)
        res = self._try_function(node.rm, (cr,), "rm %s"  % uri, cr=cr)
        if not res:
            if cr: cr.close()
            raise OSError(1, 'Operation not permited.')        
        cr.commit()
        cr.close()
        return 204

    ### DELETE handlers (examples)
    ### (we use the predefined methods in davcmd instead of doing
    ### a rm directly
    ###

    def delone(self, uri):
        """ delete a single resource

        You have to return a result dict of the form
        uri:error_code
        or None if everything's ok

        """
        if uri[-1]=='/':uri=uri[:-1]
        res=delone(self,uri)
        # parent='/'.join(uri.split('/')[:-1])
        return res

    def deltree(self, uri):
        """ delete a collection

        You have to return a result dict of the form
        uri:error_code
        or None if everything's ok
        """
        if uri[-1]=='/':uri=uri[:-1]
        res=deltree(self, uri)
        # parent='/'.join(uri.split('/')[:-1])
        return res


    ###
    ### MOVE handlers (examples)
    ###

    def moveone(self, src, dst, overwrite):
        """ move one resource with Depth=0

        an alternative implementation would be

        result_code=201
        if overwrite:
            result_code=204
            r=os.system("rm -f '%s'" %dst)
            if r: return 412
        r=os.system("mv '%s' '%s'" %(src,dst))
        if r: return 412
        return result_code

        (untested!). This would not use the davcmd functions
        and thus can only detect errors directly on the root node.
        """
        res=moveone(self, src, dst, overwrite)
        return res

    def movetree(self, src, dst, overwrite):
        """ move a collection with Depth=infinity

        an alternative implementation would be

        result_code=201
        if overwrite:
            result_code=204
            r=os.system("rm -rf '%s'" %dst)
            if r: return 412
        r=os.system("mv '%s' '%s'" %(src,dst))
        if r: return 412
        return result_code

        (untested!). This would not use the davcmd functions
        and thus can only detect errors directly on the root node"""

        res=movetree(self, src, dst, overwrite)
        return res

    ###
    ### COPY handlers
    ###

    def copyone(self, src, dst, overwrite):
        """ copy one resource with Depth=0

        an alternative implementation would be

        result_code=201
        if overwrite:
            result_code=204
            r=os.system("rm -f '%s'" %dst)
            if r: return 412
        r=os.system("cp '%s' '%s'" %(src,dst))
        if r: return 412
        return result_code

        (untested!). This would not use the davcmd functions
        and thus can only detect errors directly on the root node.
        """
        res=copyone(self, src, dst, overwrite)
        return res

    def copytree(self, src, dst, overwrite):
        """ copy a collection with Depth=infinity

        an alternative implementation would be

        result_code=201
        if overwrite:
            result_code=204
            r=os.system("rm -rf '%s'" %dst)
            if r: return 412
        r=os.system("cp -r '%s' '%s'" %(src,dst))
        if r: return 412
        return result_code

        (untested!). This would not use the davcmd functions
        and thus can only detect errors directly on the root node"""
        res=copytree(self, src, dst, overwrite)
        return res

    ###
    ### copy methods.
    ### This methods actually copy something. low-level
    ### They are called by the davcmd utility functions
    ### copytree and copyone (not the above!)
    ### Look in davcmd.py for further details.
    ###

    def copy(self, src, dst):
        src=urllib.unquote(src)
        dst=urllib.unquote(dst)
        ct = self._get_dav_getcontenttype(src)
        data = self.get_data(src)
        self.put(dst, data, ct)
        return 201

    def copycol(self, src, dst):
        """ copy a collection.

        As this is not recursive (the davserver recurses itself)
        we will only create a new directory here. For some more
        advanced systems we might also have to copy properties from
        the source to the destination.
        """
        return self.mkcol(dst)


    def exists(self, uri):
        """ test if a resource exists """
        result = False
        cr, uid, pool,dbname, uri2 = self.get_cr(uri)
        if not dbname:
            if cr: cr.close()
            return True
        try:
            node = self.uri2object(cr, uid, pool, uri2)
            if node:
                result = True
        except Exception:
            pass
        cr.close()
        return result

    def unlock(self, uri, token):
        """ Unlock a resource from that token 
        
        @return True if unlocked, False if no lock existed, Exceptions
        """
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        if not dbname:
            if cr: cr.close()
            raise DAV_Error, 409

        node = self.uri2object(cr, uid, pool, uri2)
        try:
            node_fn = node.dav_unlock
        except AttributeError:
            # perhaps the node doesn't support locks
            cr.close()
            raise DAV_Error(400, 'No locks for this resource')

        res = self._try_function(node_fn, (cr, token), "unlock %s" % uri, cr=cr)
        cr.commit()
        cr.close()
        return res

    def lock(self, uri, lock_data):
        """ Lock (may create) resource.
            Data is a dict, may contain:
                depth, token, refresh, lockscope, locktype, owner
        """
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        created = False
        if not dbname:
            if cr: cr.close()
            raise DAV_Error, 409

        try:
            node = self.uri2object(cr, uid, pool, uri2[:])
        except Exception:
            node = False
        
        objname = misc.ustr(uri2[-1])
        
        if not node:
            dir_node = self.uri2object(cr, uid, pool, uri2[:-1])
            if not dir_node:
                cr.close()
                raise DAV_NotFound('Parent folder not found')

            # We create a new node (file) but with empty data=None,
            # as in RFC4918 p. 9.10.4
            node = self._try_function(dir_node.create_child, (cr, objname, None),
                    "create %s" % objname, cr=cr)
            if not node:
                cr.commit()
                cr.close()
                raise DAV_Error(400, "Failed to create resource")
            
            created = True

        try:
            node_fn = node.dav_lock
        except AttributeError:
            # perhaps the node doesn't support locks
            cr.close()
            raise DAV_Error(400, 'No locks for this resource')

        # Obtain the lock on the node
        lres, pid, token = self._try_function(node_fn, (cr, lock_data), "lock %s" % objname, cr=cr)

        if not lres:
            cr.commit()
            cr.close()
            raise DAV_Error(423, "Resource already locked")
        
        assert isinstance(lres, list), 'lres: %s' % repr(lres)
        
        try:
            data = mk_lock_response(self, uri, lres)
            cr.commit()
        except Exception:
            cr.close()
            raise

        cr.close()
        return created, data, token

    @memoize(CACHE_SIZE)
    def is_collection(self, uri):
        """ test if the given uri is a collection """
        cr, uid, pool, dbname, uri2 = self.get_cr(uri)
        try:
            if not dbname:
                return True
            node = self.uri2object(cr,uid,pool, uri2)
            if not node:
                raise DAV_NotFound2(uri2)
            if node.type in ('collection','database'):
                return True
            return False
        finally:
            if cr: cr.close()

#eof
