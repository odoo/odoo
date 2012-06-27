# -*- encoding: utf-8 -*-

import os
import time
from tarfile import filemode
import logging
import errno

import glob
import fnmatch

import pooler
import netsvc
import sql_db

from service import security
from osv import osv
from document.nodes import get_node_context

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

from ftpserver import _to_decode, _to_unicode


class abstracted_fs(object):
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

    def __init__(self):
        self.root = None
        self.cwd = '/'
        self.cwd_node = None
        self.rnfr = None
        self._log = logging.getLogger(__name__)

    # Ok
    def db_list(self):
        """Get the list of available databases, with FTPd support
        """
        s = netsvc.ExportService.getService('db')
        result = s.exp_list(document=True)
        self.db_name_list = []
        for db_name in result:
            db, cr = None, None
            try:
                try:
                    db = sql_db.db_connect(db_name)
                    cr = db.cursor()
                    cr.execute("SELECT 1 FROM pg_class WHERE relkind = 'r' AND relname = 'ir_module_module'")
                    if not cr.fetchone():
                        continue

                    cr.execute("SELECT id FROM ir_module_module WHERE name = 'document_ftp' AND state IN ('installed', 'to install', 'to upgrade') ")
                    res = cr.fetchone()
                    if res and len(res):
                        self.db_name_list.append(db_name)
                    cr.commit()
                except Exception:
                    self._log.warning('Cannot use db "%s"', db_name)
            finally:
                if cr is not None:
                    cr.close()
        return self.db_name_list

    def ftpnorm(self, ftppath):
        """Normalize a "virtual" ftp pathname (tipically the raw string
        coming from client).

        Pathname returned is relative!.
        """
        p = os.path.normpath(ftppath)
        # normalize string in a standard web-path notation having '/'
        # as separator. xrg: is that really in the spec?
        p = p.replace("\\", "/")
        # os.path.normpath supports UNC paths (e.g. "//a/b/c") but we
        # don't need them.  In case we get an UNC path we collapse
        # redundant separators appearing at the beginning of the string
        while p[:2] == '//':
            p = p[1:]
        if p == '.':
            return ''
        return p

    def get_cwd(self):
        """ return the cwd, decoded in utf"""
        return _to_decode(self.cwd)

    def ftp2fs(self, path_orig, data):
        raise DeprecationWarning()

    def fs2ftp(self, node):
        """ Return the string path of a node, in ftp form
        """
        res='/'
        if node:
            paths = node.full_path()
            res = '/' + node.context.dbname + '/' +  \
                _to_decode(os.path.join(*paths))

        return res

    def validpath(self, path):
        """Check whether the path belongs to user's home directory.
        Expected argument is a datacr tuple
        """
        # TODO: are we called for "/" ?
        return isinstance(path, tuple) and path[1] and True or False

    # --- Wrapper methods around open() and tempfile.mkstemp

    def create(self, datacr, objname, mode):
        """ Create a children file-node under node, open it
            @return open node_descriptor of the created node
        """
        objname = _to_unicode(objname)
        cr , node, rem = datacr
        try:
            child = node.child(cr, objname)
            if child:
                if child.type not in ('file','content'):
                    raise OSError(1, 'Operation not permited.')

                ret = child.open_data(cr, mode)
                cr.commit()
                assert ret, "Cannot create descriptor for %r: %r" % (child, ret)
                return ret
        except EnvironmentError:
            raise
        except Exception:
            self._log.exception('Cannot locate item %s at node %s', objname, repr(node))
            pass

        try:
            child = node.create_child(cr, objname, data=None)
            ret = child.open_data(cr, mode)
            assert ret, "cannot create descriptor for %r" % child
            cr.commit()
            return ret
        except EnvironmentError:
            raise
        except Exception:
            self._log.exception('Cannot create item %s at node %s', objname, repr(node))
            raise OSError(1, 'Operation not permited.')

    def open(self, datacr, mode):
        if not (datacr and datacr[1]):
            raise OSError(1, 'Operation not permited.')
        # Reading operation
        cr, node, rem = datacr
        try:
            res = node.open_data(cr, mode)
            cr.commit()
        except TypeError:
            raise IOError(errno.EINVAL, "No data")
        return res

    # ok, but need test more

    def mkstemp(self, suffix='', prefix='', dir=None, mode='wb'):
        """A wrap around tempfile.mkstemp creating a file with a unique
        name.  Unlike mkstemp it returns an object with a file-like
        interface.
        """
        raise NotImplementedError # TODO

        text = not 'b' in mode
        # for unique file , maintain version if duplicate file
        if dir:
            cr = dir.cr
            uid = dir.uid
            pool = pooler.get_pool(node.context.dbname)
            object=dir and dir.object or False
            object2=dir and dir.object2 or False
            res=pool.get('ir.attachment').search(cr,uid,[('name','like',prefix),('parent_id','=',object and object.type in ('directory','ressource') and object.id or False),('res_id','=',object2 and object2.id or False),('res_model','=',object2 and object2._name or False)])
            if len(res):
                pre = prefix.split('.')
                prefix=pre[0] + '.v'+str(len(res))+'.'+pre[1]
        return self.create(dir,suffix+prefix,text)



    # Ok
    def chdir(self, datacr):
        if (not datacr) or datacr == (None, None, None):
            self.cwd = '/'
            self.cwd_node = None
            return None
        if not datacr[1]:
            raise OSError(1, 'Operation not permitted')
        if datacr[1].type not in  ('collection','database'):
            raise OSError(2, 'Path is not a directory')
        self.cwd = '/'+datacr[1].context.dbname + '/'
        self.cwd += '/'.join(datacr[1].full_path())
        self.cwd_node = datacr[1]

    # Ok
    def mkdir(self, datacr, basename):
        """Create the specified directory."""
        cr, node, rem = datacr or (None, None, None)
        if not node:
            raise OSError(1, 'Operation not permited.')

        try:
            basename =_to_unicode(basename)
            cdir = node.create_child_collection(cr, basename)
            self._log.debug("Created child dir: %r", cdir)
            cr.commit()
        except Exception:
            self._log.exception('Cannot create dir "%s" at node %s', basename, repr(node))
            raise OSError(1, 'Operation not permited.')

    def close_cr(self, data):
        if data and data[0]:
            data[0].close()
        return True

    def get_cr(self, pathname):
        raise DeprecationWarning()

    def get_crdata(self, line, mode='file'):
        """ Get database cursor, node and remainder data, for commands

        This is the helper function that will prepare the arguments for
        any of the subsequent commands.
        It returns a tuple in the form of:
        @code        ( cr, node, rem_path=None )

        @param line An absolute or relative ftp path, as passed to the cmd.
        @param mode A word describing the mode of operation, so that this
                    function behaves properly in the different commands.
        """
        path = self.ftpnorm(line)
        if self.cwd_node is None:
            if not os.path.isabs(path):
                path = os.path.join(self.root, path)

        if path == '/' and mode in ('list', 'cwd'):
            return (None, None, None )

        path = _to_unicode(os.path.normpath(path)) # again, for '/db/../ss'
        if path == '.': path = ''

        if os.path.isabs(path) and self.cwd_node is not None \
                and path.startswith(self.cwd):
            # make relative, so that cwd_node is used again
            path = path[len(self.cwd):]
            if path.startswith('/'):
                path = path[1:]

        p_parts = path.split('/') # hard-code the unix sep here, by spec.

        assert '..' not in p_parts

        rem_path = None
        if mode in ('create',):
            rem_path = p_parts[-1]
            p_parts = p_parts[:-1]

        if os.path.isabs(path):
            # we have to start from root, again
            while p_parts and p_parts[0] == '':
                p_parts = p_parts[1:]
            # self._log.debug("Path parts: %r ", p_parts)
            if not p_parts:
                raise IOError(errno.EPERM, 'Cannot perform operation at root dir')
            dbname = p_parts[0]
            if dbname not in self.db_list():
                raise IOError(errno.ENOENT,'Invalid database path: %s' % dbname)
            try:
                db = pooler.get_db(dbname)
            except Exception:
                raise OSError(1, 'Database cannot be used.')
            cr = db.cursor()
            try:
                uid = security.login(dbname, self.username, self.password)
            except Exception:
                cr.close()
                raise
            if not uid:
                cr.close()
                raise OSError(2, 'Authentification Required.')
            n = get_node_context(cr, uid, {})
            node = n.get_uri(cr, p_parts[1:])
            return (cr, node, rem_path)
        else:
            # we never reach here if cwd_node is not set
            if p_parts and p_parts[-1] == '':
                p_parts = p_parts[:-1]
            cr, uid = self.get_node_cr_uid(self.cwd_node)
            if p_parts:
                node = self.cwd_node.get_uri(cr, p_parts)
            else:
                node = self.cwd_node
            if node is False and mode not in ('???'):
                cr.close()
                raise IOError(errno.ENOENT, 'Path does not exist')
            return (cr, node, rem_path)

    def get_node_cr_uid(self, node):
        """ Get cr, uid, pool from a node
        """
        assert node
        db = pooler.get_db(node.context.dbname)
        return db.cursor(), node.context.uid

    def get_node_cr(self, node):
        """ Get the cursor for the database of a node

        The cursor is the only thing that a node will not store
        persistenly, so we have to obtain a new one for each call.
        """
        return self.get_node_cr_uid(node)[0]

    def listdir(self, datacr):
        """List the content of a directory."""
        class false_node(object):
            write_date = 0.0
            create_date = 0.0
            unixperms = 040550
            content_length = 0L
            uuser = 'root'
            ugroup = 'root'
            type = 'database'

            def __init__(self, db):
                self.path = db

        if datacr[1] is None:
            result = []
            for db in self.db_list():
                try:
                    result.append(false_node(db))
                except osv.except_osv:
                    pass
            return result
        cr, node, rem = datacr
        res = node.children(cr)
        return res

    def rmdir(self, datacr):
        """Remove the specified directory."""
        cr, node, rem = datacr
        assert node
        node.rmcol(cr)
        cr.commit()

    def remove(self, datacr):
        assert datacr[1]
        if datacr[1].type == 'collection':
            return self.rmdir(datacr)
        elif datacr[1].type == 'file':
            return self.rmfile(datacr)
        raise OSError(1, 'Operation not permited.')

    def rmfile(self, datacr):
        """Remove the specified file."""
        assert datacr[1]
        cr = datacr[0]
        datacr[1].rm(cr)
        cr.commit()

    def rename(self, src, datacr):
        """ Renaming operation, the effect depends on the src:
            * A file: read, create and remove
            * A directory: change the parent and reassign children to ressource
        """
        cr = datacr[0]
        try:
            nname = _to_unicode(datacr[2])
            ret = src.move_to(cr, datacr[1], new_name=nname)
            # API shouldn't wait for us to write the object
            assert (ret is True) or (ret is False)
            cr.commit()
        except EnvironmentError:
            raise
        except Exception:
            self._log.exception('Cannot rename "%s" to "%s" at "%s"', src, datacr[2], datacr[1])
            raise OSError(1,'Operation not permited.')

    def stat(self, node):
        raise NotImplementedError()

    # --- Wrapper methods around os.path.*

    # Ok
    def isfile(self, node):
        if node and (node.type in ('file','content')):
            return True
        return False

    # Ok
    def islink(self, path):
        """Return True if path is a symbolic link."""
        return False

    def isdir(self, node):
        """Return True if path is a directory."""
        if node is None:
            return True
        if node and (node.type in ('collection','database')):
            return True
        return False

    def getsize(self, datacr):
        """Return the size of the specified file in bytes."""
        if not (datacr and datacr[1]):
            raise IOError(errno.ENOENT, "No such file or directory")
        if datacr[1].type in ('file', 'content'):
            return datacr[1].get_data_len(datacr[0]) or 0L
        return 0L

    # Ok
    def getmtime(self, datacr):
        """Return the last modified time as a number of seconds since
        the epoch."""

        node = datacr[1]
        if node.write_date or node.create_date:
            dt = (node.write_date or node.create_date)[:19]
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
        raise DeprecationWarning()
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

    def get_list_dir(self, datacr):
        """"Return an iterator object that yields a directory listing
        in a form suitable for LIST command.
        """
        if not datacr:
            return None
        elif self.isdir(datacr[1]):
            listing = self.listdir(datacr)
            return self.format_list(datacr[0], datacr[1], listing)
        # if path is a file or a symlink we return information about it
        elif self.isfile(datacr[1]):
            par = datacr[1].parent
            return self.format_list(datacr[0], par, [datacr[1]])

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

    def format_list(self, cr, parent_node, listing, ignore_err=True):
        """Return an iterator object that yields the entries of given
        directory emulating the "/bin/ls -lA" UNIX command output.

         - (str) basedir: the parent directory node. Can be None
         - (list) listing: a list of nodes
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
        for node in listing:
            perms = filemode(node.unixperms)  # permissions
            nlinks = 1
            size = node.content_length or 0L
            uname = _to_decode(node.uuser)
            gname = _to_decode(node.ugroup)
            # stat.st_mtime could fail (-1) if last mtime is too old
            # in which case we return the local time as last mtime
            try:
                st_mtime = node.write_date or 0.0
                if isinstance(st_mtime, basestring):
                    st_mtime = time.strptime(st_mtime, '%Y-%m-%d %H:%M:%S')
                elif isinstance(st_mtime, float):
                    st_mtime = time.localtime(st_mtime)
                mname=_get_month_name(time.strftime("%m", st_mtime ))
                mtime = mname+' '+time.strftime("%d %H:%M", st_mtime)
            except ValueError:
                mname=_get_month_name(time.strftime("%m"))
                mtime = mname+' '+time.strftime("%d %H:%M")
            fpath = node.path
            if isinstance(fpath, (list, tuple)):
                fpath = fpath[-1]
            # formatting is matched with proftpd ls output
            path=_to_decode(fpath)
            yield "%s %3s %-8s %-8s %8s %s %s\r\n" %(perms, nlinks, uname, gname,
                                                     size, mtime, path)

    # Ok
    def format_mlsx(self, cr, basedir, listing, perms, facts, ignore_err=True):
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
        for node in listing:
            # type + perm
            if self.isdir(node):
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
                size = 'size=%s;' % (node.content_length or 0L)
            # last modification time
            if 'modify' in facts:
                try:
                    st_mtime = node.write_date or 0.0
                    if isinstance(st_mtime, basestring):
                        st_mtime = time.strptime(st_mtime, '%Y-%m-%d %H:%M:%S')
                    elif isinstance(st_mtime, float):
                        st_mtime = time.localtime(st_mtime)
                    modify = 'modify=%s;' %time.strftime("%Y%m%d%H%M%S", st_mtime)
                except ValueError:
                    # stat.st_mtime could fail (-1) if last mtime is too old
                    modify = ""
            if 'create' in facts:
                # on Windows we can provide also the creation time
                try:
                    st_ctime = node.create_date or 0.0
                    if isinstance(st_ctime, basestring):
                        st_ctime = time.strptime(st_ctime, '%Y-%m-%d %H:%M:%S')
                    elif isinstance(st_mtime, float):
                        st_ctime = time.localtime(st_ctime)
                    create = 'create=%s;' %time.strftime("%Y%m%d%H%M%S",st_ctime)
                except ValueError:
                    create = ""
            # UNIX only
            if 'unix.mode' in facts:
                mode = 'unix.mode=%s;' %oct(node.unixperms & 0777)
            if 'unix.uid' in facts:
                uid = 'unix.uid=%s;' % _to_decode(node.uuser)
            if 'unix.gid' in facts:
                gid = 'unix.gid=%s;' % _to_decode(node.ugroup)
            # We provide unique fact (see RFC-3659, chapter 7.5.2) on
            # posix platforms only; we get it by mixing st_dev and
            # st_ino values which should be enough for granting an
            # uniqueness for the file listed.
            # The same approach is used by pure-ftpd.
            # Implementors who want to provide unique fact on other
            # platforms should use some platform-specific method (e.g.
            # on Windows NTFS filesystems MTF records could be used).
            # if 'unique' in facts: todo
            #    unique = "unique=%x%x;" %(st.st_dev, st.st_ino)
            path = node.path
            if isinstance (path, (list, tuple)):
                path = path[-1]
            path=_to_decode(path)
            yield "%s%s%s%s%s%s%s%s%s %s\r\n" %(type, size, perm, modify, create,
                                                mode, uid, gid, unique, path)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

