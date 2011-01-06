# -*- encoding: utf-8 -*-
import os
import time
from tarfile import filemode
import StringIO
import base64

import glob
import fnmatch

import pooler
import netsvc
import os
from service import security
from osv import osv
import stat

def log(message):
    logger = netsvc.Logger()
    logger.notifyChannel('DMS', netsvc.LOG_ERROR, message)


def _get_month_name(month):
    month=int(month)
    if month==1:return 'Jan'
    elif month==2:return 'Feb'
    elif month==3:return 'Mar'
    elif month==4:return 'Apr'
    elif month==5:return 'May'
    elif month==6:return 'Jun'
    elif month==7:return 'Jul'
    elif month==8:return 'Aug'
    elif month==9:return 'Sep'
    elif month==10:return 'Oct'
    elif month==11:return 'Nov'
    elif month==12:return 'Dec'

def _to_unicode(s):
    try:
        return s.decode('utf-8')
    except UnicodeError:
        try:
            return s.decode('latin')
        except UnicodeError:
            try:
                return s.encode('ascii')
            except UnicodeError:
                return s

def _to_decode(s):
    try:
        return s.encode('utf-8')
    except UnicodeError:
        try:
            return s.encode('latin')
        except UnicodeError:
            try:
                return s.decode('ascii')
            except UnicodeError:
                return s  
    
			
class file_wrapper(StringIO.StringIO):
    def __init__(self, sstr='', ressource_id=False, dbname=None, uid=1, name=''):
        StringIO.StringIO.__init__(self, sstr)
        self.ressource_id = ressource_id
        self.name = name
        self.dbname = dbname
        self.uid = uid
    def close(self, *args, **kwargs):
        db,pool = pooler.get_db_and_pool(self.dbname)
        cr = db.cursor()
        cr.commit()
        try:
            val = self.getvalue()
            val2 = {
                'datas': base64.encodestring(val),
                'file_size': len(val),
            }
            pool.get('ir.attachment').write(cr, self.uid, [self.ressource_id], val2)
        finally:
            cr.commit()
            cr.close()
        StringIO.StringIO.close(self, *args, **kwargs)

class content_wrapper(StringIO.StringIO):
    def __init__(self, dbname, uid, pool, node, name=''):
        StringIO.StringIO.__init__(self, '')
        self.dbname = dbname
        self.uid = uid
        self.node = node
        self.pool = pool
        self.name = name
    def close(self, *args, **kwargs):
        db,pool = pooler.get_db_and_pool(self.dbname)
        cr = db.cursor()
        cr.commit()
        try:
            getattr(self.pool.get('document.directory.content'), 'process_write_'+self.node.content.extension[1:])(cr, self.uid, self.node, self.getvalue())
        finally:
            cr.commit()
            cr.close()
        StringIO.StringIO.close(self, *args, **kwargs)


class abstracted_fs:
    """A class used to interact with the file system, providing a high
    level, cross-platform interface compatible with both Windows and
    UNIX style filesystems.

    It provides some utility methods and some wraps around operations
    involved in file creation and file system operations like moving
    files or removing directories.

    Instance attributes:
     - (str) root: the user home directory.
     - (str) cwd: the current working directory.
     - (str) rnfr: source file to be renamed.
    """

    # Ok
    def db_list(self):
        #return pooler.pool_dic.keys()
        s = netsvc.LocalService('db')
        result = s.list(document=True)
        self.db_name_list = []
        for db_name in result:
            db, cr = None, None
            try:
                try:
                    db = pooler.get_db_only(db_name)
                    cr = db.cursor()
                    cr.execute("SELECT 1 FROM pg_class WHERE relkind = 'r' AND relname = 'ir_module_module'")
                    if not cr.fetchone():
                        continue
    
                    cr.execute("select id from ir_module_module where name like 'document%' and state='installed' ")
                    res = cr.fetchone()
                    if res and len(res):
                        self.db_name_list.append(db_name)
                    cr.commit()
                except Exception, e:
                    log(e)
            finally:
                if cr is not None:
                    cr.close()
                #if db is not None:
                #    pooler.close_db(db_name)        
        return self.db_name_list

    # Ok
    def __init__(self):
        self.root = None
        self.cwd = '/'
        self.rnfr = None

    # --- Pathname / conversion utilities

    # Ok
    def ftpnorm(self, ftppath):
        """Normalize a "virtual" ftp pathname (tipically the raw string
        coming from client) depending on the current working directory.

        Example (having "/foo" as current working directory):
        'x' -> '/foo/x'

        Note: directory separators are system independent ("/").
        Pathname returned is always absolutized.
        """
        if os.path.isabs(ftppath):
            p = os.path.normpath(ftppath)
        else:
            p = os.path.normpath(os.path.join(self.cwd, ftppath))
        # normalize string in a standard web-path notation having '/'
        # as separator.
        p = p.replace("\\", "/")
        # os.path.normpath supports UNC paths (e.g. "//a/b/c") but we
        # don't need them.  In case we get an UNC path we collapse
        # redundant separators appearing at the beginning of the string
        while p[:2] == '//':
            p = p[1:]
        # Anti path traversal: don't trust user input, in the event
        # that self.cwd is not absolute, return "/" as a safety measure.
        # This is for extra protection, maybe not really necessary.
        if not os.path.isabs(p):
            p = "/"
        return p

    # Ok
    def ftp2fs(self, path_orig, data):
        path = self.ftpnorm(path_orig)
        if not data or (path and path=='/'):
            return None               
        path2 = filter(None,path.split('/'))[1:]
        (cr, uid, pool) = data
        if len(path2):     
            path2[-1]=_to_unicode(path2[-1])
        res = pool.get('document.directory').get_object(cr, uid, path2[:])
        if not res:
            raise OSError(2, 'Not such file or directory.')
        return res

    # Ok
    def fs2ftp(self, node):        
        res='/'
        if node:
            res=os.path.normpath(node.path)
            res = res.replace("\\", "/")        
            while res[:2] == '//':
                res = res[1:]
            res='/' + node.cr.dbname + '/' + _to_decode(res)            
            
        #res = node and ('/' + node.cr.dbname + '/' + _to_decode(self.ftpnorm(node.path))) or '/'
        return res

    # Ok
    def validpath(self, path):
        """Check whether the path belongs to user's home directory.
        Expected argument is a "real" filesystem pathname.

        If path is a symbolic link it is resolved to check its real
        destination.

        Pathnames escaping from user's root directory are considered
        not valid.
        """
        return path and True or False

    # --- Wrapper methods around open() and tempfile.mkstemp

    # Ok
    def create(self, node, objname, mode):
        objname=_to_unicode(objname)
        cr = node.cr
        uid = node.uid
        pool = pooler.get_pool(cr.dbname)
        child = node.child(objname)
        if child:
            if child.type in ('collection','database'):
                raise OSError(1, 'Operation not permited.')
            if child.type=='content':
                s = content_wrapper(cr.dbname, uid, pool, child)
                return s
        try:
            fobj = pool.get('ir.attachment')
            ext = objname.find('.') >0 and objname.split('.')[1] or False

            # TODO: test if already exist and modify in this case if node.type=file
            ### checked already exits
            object2=node and node.object2 or False
            object=node and node.object or False
            cid=False

            where=[('name','=',objname)]
            if object and (object.type in ('directory')) or object2:
                where.append(('parent_id','=',object.id))
            else:
                where.append(('parent_id','=',False))

            if object2:
                where +=[('res_id','=',object2.id),('res_model','=',object2._name)]
            cids = fobj.search(cr, uid,where)
            if len(cids):
                cid=cids[0]

            if not cid:
                val = {
                    'name': objname,
                    'datas_fname': objname,
                    'datas': '',
                    'file_size': 0L,
                    'file_type': ext,
                }
                if object and (object.type in ('directory')) or not object2:
                    val['parent_id']= object and object.id or False
                partner = False
                if object2:
                    if 'partner_id' in object2 and object2.partner_id.id:
                        partner = object2.partner_id.id
                    if object2._name == 'res.partner':
                        partner = object2.id
                    val.update( {
                        'res_model': object2._name,
                        'partner_id': partner,
                        'res_id': object2.id
                    })
                cid = fobj.create(cr, uid, val, context={})
            cr.commit()

            s = file_wrapper('', cid, cr.dbname, uid, )
            return s
        except Exception,e:             
            log(e)
            raise OSError(1, 'Operation not permited.')

    # Ok
    def open(self, node, mode):
        if not node:
            raise OSError(1, 'Operation not permited.')
        # Reading operation
        if node.type=='file':
            if not self.isfile(node):
                raise OSError(1, 'Operation not permited.')
            s = StringIO.StringIO(base64.decodestring(node.object.datas or ''))
            s.name = node
            return s
        elif node.type=='content':
            cr = node.cr
            uid = node.uid
            pool = pooler.get_pool(cr.dbname)
            return getattr(pool.get('document.directory.content'), 'process_read_'+node.content.extension[1:])(cr, uid, node)
        else:
            raise OSError(1, 'Operation not permited.')

    # ok, but need test more

    def mkstemp(self, suffix='', prefix='', dir=None, mode='wb'):
        """A wrap around tempfile.mkstemp creating a file with a unique
        name.  Unlike mkstemp it returns an object with a file-like
        interface.
        """
        raise 'Not Yet Implemented'
#        class FileWrapper:
#            def __init__(self, fd, name):
#                self.file = fd
#                self.name = name
#            def __getattr__(self, attr):
#                return getattr(self.file, attr)
#
#        text = not 'b' in mode
#        # max number of tries to find out a unique file name
#        tempfile.TMP_MAX = 50
#        fd, name = tempfile.mkstemp(suffix, prefix, dir, text=text)
#        file = os.fdopen(fd, mode)
#        return FileWrapper(file, name)

        text = not 'b' in mode
        # for unique file , maintain version if duplicate file
        if dir:
            cr = dir.cr
            uid = dir.uid
            pool = pooler.get_pool(cr.dbname)
            object=dir and dir.object or False
            object2=dir and dir.object2 or False
            res=pool.get('ir.attachment').search(cr,uid,[('name','like',prefix),('parent_id','=',object and object.type in ('directory','ressource') and object.id or False),('res_id','=',object2 and object2.id or False),('res_model','=',object2 and object2._name or False)])
            if len(res):
                pre = prefix.split('.')
                prefix=pre[0] + '.v'+str(len(res))+'.'+pre[1]
            #prefix = prefix + '.'
        return self.create(dir,suffix+prefix,text)



    # Ok
    def chdir(self, path):        
        if not path:
            self.cwd='/'
            return None
        if path.type in ('collection','database'):
            self.cwd = self.fs2ftp(path)
        else:
            raise OSError(1, 'Operation not permited.')

    # Ok
    def mkdir(self, node, basename):
        """Create the specified directory."""
        if not node:
            raise OSError(1, 'Operation not permited.')
        try:
            basename=_to_unicode(basename)
            object2=node and node.object2 or False
            object=node and node.object or False
            cr = node.cr
            uid = node.uid
            pool = pooler.get_pool(cr.dbname)
            if node.object and (node.object.type=='ressource') and not node.object2:
                raise OSError(1, 'Operation not permited.')
            val = {
                'name': basename,
                'ressource_parent_type_id': object and object.ressource_type_id.id or False,
                'ressource_id': object2 and object2.id or False
            }
            if (object and (object.type in ('directory'))) or not object2:                
                val['parent_id'] =  object and object.id or False
            # Check if it alreayd exists !
            pool.get('document.directory').create(cr, uid, val)
            cr.commit()
        except Exception,e:
            log(e)
            raise OSError(1, 'Operation not permited.')


    # Ok
    def close_cr(self, data):
        if data:
            data[0].close()
        return True

    def get_cr(self, path):
        path = self.ftpnorm(path)
        if path=='/':
            return None
        dbname = path.split('/')[1]
        if dbname not in self.db_list():
            return None
        try:
            db,pool = pooler.get_db_and_pool(dbname)
        except:
            raise OSError(1, 'Operation not permited.')
        cr = db.cursor()
        uid = security.login(dbname, self.username, self.password)
        if not uid:
            raise OSError(2, 'Authentification Required.')
        return cr, uid, pool

    # Ok
    def listdir(self, path):
        """List the content of a directory."""
        class false_node:
            object = None
            type = 'database'
            def __init__(self, db):
                self.path = '/'+db

        if path is None:
            result = []
            for db in self.db_list():
                try:
                    uid = security.login(db, self.username, self.password)
                    if uid:
                        result.append(false_node(db))                    
                except osv.except_osv:                    
                    pass
            return result
        return path.children()

    # Ok
    def rmdir(self, node):
        """Remove the specified directory."""
        cr = node.cr
        uid = node.uid
        pool = pooler.get_pool(cr.dbname)
        object2=node and node.object2 or False
        object=node and node.object or False
        if object._table_name=='document.directory':
            if node.children():
                raise OSError(39, 'Directory not empty.')
            res = pool.get('document.directory').unlink(cr, uid, [object.id])
        else:
            raise OSError(39, 'Directory not empty.')

        cr.commit()

    # Ok
    def remove(self, node):
        """Remove the specified file."""
        cr = node.cr
        uid = node.uid
        pool = pooler.get_pool(cr.dbname)
        object2=node and node.object2 or False
        object=node and node.object or False
        if not object:
            raise OSError(2, 'Not such file or directory.')
        if object._table_name=='ir.attachment':
            res = pool.get('ir.attachment').unlink(cr, uid, [object.id])
        else:
            raise OSError(1, 'Operation not permited.')
        cr.commit()

    # Ok
    def rename(self, src, dst_basedir,dst_basename):
        """
            Renaming operation, the effect depends on the src:
            * A file: read, create and remove
            * A directory: change the parent and reassign childs to ressource
        """
        try:
            dst_basename=_to_unicode(dst_basename)
            if src.type=='collection':
                if src.object._table_name <> 'document.directory':
                    raise OSError(1, 'Operation not permited.')
                result = {
                    'directory': [],
                    'attachment': []
                }
                # Compute all childs to set the new ressource ID
                child_ids = [src]
                while len(child_ids):
                    node = child_ids.pop(0)
                    child_ids += node.children()
                    if node.type =='collection':
                        result['directory'].append(node.object.id)
                        if (not node.object.ressource_id) and node.object2:
                            raise OSError(1, 'Operation not permited.')
                    elif node.type =='file':
                        result['attachment'].append(node.object.id)

                cr = src.cr
                uid = src.uid
                pool = pooler.get_pool(cr.dbname)
                object2=src and src.object2 or False
                object=src and src.object or False
                if object2 and not object.ressource_id:
                    raise OSError(1, 'Operation not permited.')
                val = {
                    'name':dst_basename,
                }
                if (dst_basedir.object and (dst_basedir.object.type in ('directory'))) or not dst_basedir.object2:
                    val['parent_id'] = dst_basedir.object and dst_basedir.object.id or False
                else:
                    val['parent_id'] = False
                res = pool.get('document.directory').write(cr, uid, [object.id],val)

                if dst_basedir.object2:
                    ressource_type_id = pool.get('ir.model').search(cr,uid,[('model','=',dst_basedir.object2._name)])[0]
                    ressource_id = dst_basedir.object2.id
                    title = dst_basedir.object2.name
                    ressource_model = dst_basedir.object2._name                    
                    if dst_basedir.object2._name=='res.partner':
                        partner_id=dst_basedir.object2.id
                    else:
                        obj2=pool.get(dst_basedir.object2._name)                         
                        partner_id= obj2.fields_get(cr,uid,['partner_id']) and dst_basedir.object2.partner_id.id or False
                else:
                    ressource_type_id = False
                    ressource_id=False
                    ressource_model = False
                    partner_id = False
                    title = False

                pool.get('document.directory').write(cr, uid, result['directory'], {
                    'ressource_id': ressource_id,
                    'ressource_type_id': ressource_type_id
                })
                val = {
                    'res_id': ressource_id,
                    'res_model': ressource_model,
                    'title': title,
                    'partner_id': partner_id
                }
                pool.get('ir.attachment').write(cr, uid, result['attachment'], val)
                if (not val['res_id']) and result['attachment']:
                    dst_basedir.cr.execute('update ir_attachment set res_id=NULL where id in ('+','.join(map(str,result['attachment']))+')')

                cr.commit()
            elif src.type=='file':
                pool = pooler.get_pool(src.cr.dbname)
                val = {
                    'partner_id':False,
                    #'res_id': False,
                    'res_model': False,
                    'name': dst_basename,
                    'datas_fname': dst_basename,
                    'title': dst_basename,
                }

                if (dst_basedir.object and (dst_basedir.object.type in ('directory','ressource'))) or not dst_basedir.object2:
                    val['parent_id'] = dst_basedir.object and dst_basedir.object.id or False
                else:
                    val['parent_id'] = False

                if dst_basedir.object2:
                    val['res_model'] = dst_basedir.object2._name
                    val['res_id'] = dst_basedir.object2.id
                    val['title'] = dst_basedir.object2.name
                    if dst_basedir.object2._name=='res.partner':
                        val['partner_id']=dst_basedir.object2.id
                    else:
                        obj2=pool.get(dst_basedir.object2._name) 
                        val['partner_id']= obj2.fields_get(src.cr, src.uid,['partner_id']) and dst_basedir.object2.partner_id.id or False
                elif src.object.res_id:
                    # I had to do that because writing False to an integer writes 0 instead of NULL
                    # change if one day we decide to improve osv/fields.py
                    dst_basedir.cr.execute('update ir_attachment set res_id=NULL where id=%s', (src.object.id,))

                pool.get('ir.attachment').write(src.cr, src.uid, [src.object.id], val)
                src.cr.commit()
            elif src.type=='content':
                src_file=self.open(src,'r')
                dst_file=self.create(dst_basedir,dst_basename,'w')
                dst_file.write(src_file.getvalue())
                dst_file.close()
                src_file.close()
                src.cr.commit()
            else:
                raise OSError(1, 'Operation not permited.')
        except Exception,err:
            log(err)
            raise OSError(1,'Operation not permited.')




    # Nearly Ok
    def stat(self, node):
        r = list(os.stat('/'))
        if self.isfile(node):
            r[0] = 33188
        r[6] = self.getsize(node)
        r[7] = self.getmtime(node)
        r[8] =  self.getmtime(node)
        r[9] =  self.getmtime(node)
        return os.stat_result(r)
    lstat = stat

    # --- Wrapper methods around os.path.*

    # Ok
    def isfile(self, node):
        if node and (node.type not in ('collection','database')):
            return True
        return False

    # Ok
    def islink(self, path):
        """Return True if path is a symbolic link."""
        return False

    # Ok
    def isdir(self, node):
        """Return True if path is a directory."""
        if node is None:
            return True
        if node and (node.type in ('collection','database')):
            return True
        return False

    # Ok
    def getsize(self, node):
        """Return the size of the specified file in bytes."""
        result = 0L
        if node.type=='file':
            result = node.object.file_size or 0L
        return result

    # Ok
    def getmtime(self, node):
        """Return the last modified time as a number of seconds since
        the epoch."""
        if node.object and node.type<>'content':
            dt = (node.object.write_date or node.object.create_date)[:19]
            result = time.mktime(time.strptime(dt, '%Y-%m-%d %H:%M:%S'))
        else:
            result = time.mktime(time.localtime())
        return result

    # Ok
    def realpath(self, path):
        """Return the canonical version of path eliminating any
        symbolic links encountered in the path (if they are
        supported by the operating system).
        """
        return path

    # Ok
    def lexists(self, path):
        """Return True if path refers to an existing path, including
        a broken or circular symbolic link.
        """
        return path and True or False
    exists = lexists

    # Ok, can be improved
    def glob1(self, dirname, pattern):
        """Return a list of files matching a dirname pattern
        non-recursively.

        Unlike glob.glob1 raises exception if os.listdir() fails.
        """
        names = self.listdir(dirname)
        if pattern[0] != '.':
            names = filter(lambda x: x.path[0] != '.', names)
        return fnmatch.filter(names, pattern)

    # --- Listing utilities

    # note: the following operations are no more blocking

    # Ok
    def get_list_dir(self, path):
        """"Return an iterator object that yields a directory listing
        in a form suitable for LIST command.
        """        
        if self.isdir(path):
            listing = self.listdir(path)
            #listing.sort()
            return self.format_list(path and path.path or '/', listing)
        # if path is a file or a symlink we return information about it
        elif self.isfile(path):
            basedir, filename = os.path.split(path.path)
            self.lstat(path)  # raise exc in case of problems
            return self.format_list(basedir, [path])


    # Ok
    def get_stat_dir(self, rawline, datacr):
        """Return an iterator object that yields a list of files
        matching a dirname pattern non-recursively in a form
        suitable for STAT command.

         - (str) rawline: the raw string passed by client as command
         argument.
        """
        ftppath = self.ftpnorm(rawline)
        if not glob.has_magic(ftppath):
            return self.get_list_dir(self.ftp2fs(rawline, datacr))
        else:
            basedir, basename = os.path.split(ftppath)
            if glob.has_magic(basedir):
                return iter(['Directory recursion not supported.\r\n'])
            else:
                basedir = self.ftp2fs(basedir, datacr)
                listing = self.glob1(basedir, basename)
                if listing:
                    listing.sort()
                return self.format_list(basedir, listing)

    # Ok    
    def format_list(self, basedir, listing, ignore_err=True):
        """Return an iterator object that yields the entries of given
        directory emulating the "/bin/ls -lA" UNIX command output.

         - (str) basedir: the absolute dirname.
         - (list) listing: the names of the entries in basedir
         - (bool) ignore_err: when False raise exception if os.lstat()
         call fails.

        On platforms which do not support the pwd and grp modules (such
        as Windows), ownership is printed as "owner" and "group" as a
        default, and number of hard links is always "1". On UNIX
        systems, the actual owner, group, and number of links are
        printed.

        This is how output appears to client:

        -rw-rw-rw-   1 owner   group    7045120 Sep 02  3:47 music.mp3
        drwxrwxrwx   1 owner   group          0 Aug 31 18:50 e-books
        -rw-rw-rw-   1 owner   group        380 Sep 02  3:40 module.py
        """
        for file in listing:
            try:
                st = self.lstat(file)
            except os.error:
                if ignore_err:
                    continue
                raise
            perms = filemode(st.st_mode)  # permissions
            nlinks = st.st_nlink  # number of links to inode
            if not nlinks:  # non-posix system, let's use a bogus value
                nlinks = 1
            size = st.st_size  # file size
            uname = "owner"
            gname = "group"
            # stat.st_mtime could fail (-1) if last mtime is too old
            # in which case we return the local time as last mtime
            try:
                mname=_get_month_name(time.strftime("%m", time.localtime(st.st_mtime)))               
                mtime = mname+' '+time.strftime("%d %H:%M", time.localtime(st.st_mtime))
            except ValueError:
                mname=_get_month_name(time.strftime("%m"))
                mtime = mname+' '+time.strftime("%d %H:%M")            
            # formatting is matched with proftpd ls output            
            path=_to_decode(file.path) #file.path.encode('ascii','replace').replace('?','_')                    
            yield "%s %3s %-8s %-8s %8s %s %s\r\n" %(perms, nlinks, uname, gname,
                                                     size, mtime, path.split('/')[-1])

    # Ok
    def format_mlsx(self, basedir, listing, perms, facts, ignore_err=True):
        """Return an iterator object that yields the entries of a given
        directory or of a single file in a form suitable with MLSD and
        MLST commands.

        Every entry includes a list of "facts" referring the listed
        element.  See RFC-3659, chapter 7, to see what every single
        fact stands for.

         - (str) basedir: the absolute dirname.
         - (list) listing: the names of the entries in basedir
         - (str) perms: the string referencing the user permissions.
         - (str) facts: the list of "facts" to be returned.
         - (bool) ignore_err: when False raise exception if os.stat()
         call fails.

        Note that "facts" returned may change depending on the platform
        and on what user specified by using the OPTS command.

        This is how output could appear to the client issuing
        a MLSD request:

        type=file;size=156;perm=r;modify=20071029155301;unique=801cd2; music.mp3
        type=dir;size=0;perm=el;modify=20071127230206;unique=801e33; ebooks
        type=file;size=211;perm=r;modify=20071103093626;unique=801e32; module.py
        """
        permdir = ''.join([x for x in perms if x not in 'arw'])
        permfile = ''.join([x for x in perms if x not in 'celmp'])
        if ('w' in perms) or ('a' in perms) or ('f' in perms):
            permdir += 'c'
        if 'd' in perms:
            permdir += 'p'
        type = size = perm = modify = create = unique = mode = uid = gid = ""
        for file in listing:                        
            try:
                st = self.stat(file)
            except OSError:
                if ignore_err:
                    continue
                raise
            # type + perm
            if stat.S_ISDIR(st.st_mode):
                if 'type' in facts:
                    type = 'type=dir;'                    
                if 'perm' in facts:
                    perm = 'perm=%s;' %permdir
            else:
                if 'type' in facts:
                    type = 'type=file;'
                if 'perm' in facts:
                    perm = 'perm=%s;' %permfile
            if 'size' in facts:
                size = 'size=%s;' %st.st_size  # file size
            # last modification time
            if 'modify' in facts:
                try:
                    modify = 'modify=%s;' %time.strftime("%Y%m%d%H%M%S",
                                           time.localtime(st.st_mtime))
                except ValueError:
                    # stat.st_mtime could fail (-1) if last mtime is too old
                    modify = ""
            if 'create' in facts:
                # on Windows we can provide also the creation time
                try:
                    create = 'create=%s;' %time.strftime("%Y%m%d%H%M%S",
                                           time.localtime(st.st_ctime))
                except ValueError:
                    create = ""
            # UNIX only
            if 'unix.mode' in facts:
                mode = 'unix.mode=%s;' %oct(st.st_mode & 0777)
            if 'unix.uid' in facts:
                uid = 'unix.uid=%s;' %st.st_uid
            if 'unix.gid' in facts:
                gid = 'unix.gid=%s;' %st.st_gid
            # We provide unique fact (see RFC-3659, chapter 7.5.2) on
            # posix platforms only; we get it by mixing st_dev and
            # st_ino values which should be enough for granting an
            # uniqueness for the file listed.
            # The same approach is used by pure-ftpd.
            # Implementors who want to provide unique fact on other
            # platforms should use some platform-specific method (e.g.
            # on Windows NTFS filesystems MTF records could be used).
            if 'unique' in facts:
                unique = "unique=%x%x;" %(st.st_dev, st.st_ino)
            path=_to_decode(file.path)
            path = path and path.split('/')[-1] or None
            yield "%s%s%s%s%s%s%s%s%s %s\r\n" %(type, size, perm, modify, create,
                                                mode, uid, gid, unique, path)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

