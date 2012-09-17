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
import logging
import os
import tempfile
from subprocess import Popen, PIPE
_logger = logging.getLogger(__name__)
class NhException(Exception):
    pass


class indexer(object):
    """ An indexer knows how to parse the content of some file.

        Typically, one indexer should be instantiated per file
        type.
        Override this class to add more functionality. Note that
        you should only override the Content or the File methods
        that give an optimal result. """

    def _getMimeTypes(self):
        """ Return supported mimetypes """
        return []

    def _getExtensions(self):
        return []

    def _getDefMime(self, ext):
        """ Return a mimetype for this document type, ideally the
            closest to the extension ext. """
        mts = self._getMimeTypes();
        if len (mts):
            return mts[0]
        return None

    def indexContent(self, content, filename=None, realfile = None):
        """ Use either content or the real file, to index.
            Some parsers will work better with the actual
            content, others parse a file easier. Try the
            optimal.
        """
        res = ''
        try:
            if content != None:
                return self._doIndexContent(content)
        except NhException:
            pass

        if realfile != None:
            try:
                return self._doIndexFile(realfile)
            except NhException:
                pass

            fp = open(realfile,'rb')
            try:
                content2 = fp.read()
            finally:
                fp.close()

            # The not-handled exception may be raised here
            return self._doIndexContent(content2)


        # last try, with a tmp file
        if content:
            try:
                fname,ext = filename and os.path.splitext(filename) or ('','')
                fd, rfname = tempfile.mkstemp(suffix=ext)
                os.write(fd, content)
                os.close(fd)
                res = self._doIndexFile(rfname)
                os.unlink(rfname)
                return res
            except NhException:
                pass

        raise NhException('No appropriate method to index file.')

    def _doIndexContent(self,content):
        raise NhException("Content cannot be handled here.")

    def _doIndexFile(self,fpath):
        raise NhException("Content cannot be handled here.")

    def __repr__(self):
        return "<indexer %s.%s>" %(self.__module__, self.__class__.__name__)


def mime_match(mime, mdict):
    if mdict.has_key(mime):
        return (mime, mdict[mime])
    if '/' in mime:
        mpat = mime.split('/')[0]+'/*'
        if mdict.has_key(mpat):
            return (mime, mdict[mpat])

    return (None, None)

class contentIndex(object):

    def __init__(self):
        self.mimes = {}
        self.exts = {}

    def register(self, obj):
        f = False
        for mime in obj._getMimeTypes():
            self.mimes[mime] = obj
            f = True

        for ext in obj._getExtensions():
            self.exts[ext] = obj
            f = True

        if f:
            _logger.debug('Register content indexer: %r.', obj)
        if not f:
            raise Exception("Your indexer should at least support a mimetype or extension.")

    def doIndex(self, content, filename=None, content_type=None, realfname = None, debug=False):
        fobj = None
        fname = None
        mime = None
        if content_type and self.mimes.has_key(content_type):
            mime = content_type
            fobj = self.mimes[content_type]
        elif filename:
            bname,ext = os.path.splitext(filename)
            if self.exts.has_key(ext):
                fobj = self.exts[ext]
                mime = fobj._getDefMime(ext)

        if content_type and not fobj:
            mime,fobj = mime_match(content_type, self.mimes)

        if not fobj:
            try:
                if realfname :
                    fname = realfname
                else:
                    try:
                        bname,ext = os.path.splitext(filename or 'test.tmp')
                    except Exception:
                        bname, ext = filename, 'tmp'
                    fd, fname = tempfile.mkstemp(suffix=ext)
                    os.write(fd, content)
                    os.close(fd)

                pop = Popen(['file','-b','--mime',fname], shell=False, stdout=PIPE)
                (result, _) = pop.communicate()

                mime2 = result.split(';')[0]
                _logger.debug('File gives us: %s', mime2)
                # Note that the temporary file still exists now.
                mime,fobj = mime_match(mime2, self.mimes)
                if not mime:
                    mime = mime2
            except Exception:
                _logger.exception('Cannot determine mime type.')

        try:
            if fobj:
                res = (mime, fobj.indexContent(content,filename,fname or realfname) )
            else:
                _logger.debug("Have no object, return (%s, None).", mime)
                res = (mime, None )
        except Exception:
            _logger.exception("Cannot index file %s (%s).",
                                    filename, fname or realfname)
            res = None

        # If we created a tmp file, unlink it now
        if not realfname and fname:
            try:
                os.unlink(fname)
            except Exception:
                _logger.exception("Cannot unlink %s.", fname)
        return res

cntIndex = contentIndex()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
