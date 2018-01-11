# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-TODAY OpenERP SA (http://www.openerp.com)
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

from openerp.osv import fields, osv

import os.path


class IrAttachment(osv.Model):
    """ Update partner to add a field about notification preferences """
    _name = "ir.attachment"
    _inherit = 'ir.attachment'

    _fileext_to_type = {
        '7z': 'archive',
        'aac': 'audio',
        'ace': 'archive',
        'ai': 'vector',
        'aiff': 'audio',
        'apk': 'archive',
        'app': 'binary',
        'as': 'script',
        'asf': 'video',
        'ass': 'text',
        'avi': 'video',
        'bat': 'script',
        'bin': 'binary',
        'bmp': 'image',
        'bzip2': 'archive',
        'c': 'script',
        'cab': 'archive',
        'cc': 'script',
        'ccd': 'disk',
        'cdi': 'disk',
        'cdr': 'vector',
        'cer': 'certificate',
        'cgm': 'vector',
        'cmd': 'script',
        'coffee': 'script',
        'com': 'binary',
        'cpp': 'script',
        'crl': 'certificate',
        'crt': 'certificate',
        'cs': 'script',
        'csr': 'certificate',
        'css': 'html',
        'csv': 'spreadsheet',
        'cue': 'disk',
        'd': 'script',
        'dds': 'image',
        'deb': 'archive',
        'der': 'certificate',
        'djvu': 'image',
        'dmg': 'archive',
        'dng': 'image',
        'doc': 'document',
        'docx': 'document',
        'dvi': 'print',
        'eot': 'font',
        'eps': 'vector',
        'exe': 'binary',
        'exr': 'image',
        'flac': 'audio',
        'flv': 'video',
        'gif': 'webimage',
        'gz': 'archive',
        'gzip': 'archive',
        'h': 'script',
        'htm': 'html',
        'html': 'html',
        'ico': 'image',
        'icon': 'image',
        'img': 'disk',
        'iso': 'disk',
        'jar': 'archive',
        'java': 'script',
        'jp2': 'image',
        'jpe': 'webimage',
        'jpeg': 'webimage',
        'jpg': 'webimage',
        'jpx': 'image',
        'js': 'script',
        'key': 'presentation',
        'keynote': 'presentation',
        'lisp': 'script',
        'lz': 'archive',
        'lzip': 'archive',
        'm': 'script',
        'm4a': 'audio',
        'm4v': 'video',
        'mds': 'disk',
        'mdx': 'disk',
        'mid': 'audio',
        'midi': 'audio',
        'mkv': 'video',
        'mng': 'image',
        'mp2': 'audio',
        'mp3': 'audio',
        'mp4': 'video',
        'mpe': 'video',
        'mpeg': 'video',
        'mpg': 'video',
        'nrg': 'disk',
        'numbers': 'spreadsheet',
        'odg': 'vector',
        'odm': 'document',
        'odp': 'presentation',
        'ods': 'spreadsheet',
        'odt': 'document',
        'ogg': 'audio',
        'ogm': 'video',
        'otf': 'font',
        'p12': 'certificate',
        'pak': 'archive',
        'pbm': 'image',
        'pdf': 'print',
        'pem': 'certificate',
        'pfx': 'certificate',
        'pgf': 'image',
        'pgm': 'image',
        'pk3': 'archive',
        'pk4': 'archive',
        'pl': 'script',
        'png': 'webimage',
        'pnm': 'image',
        'ppm': 'image',
        'pps': 'presentation',
        'ppt': 'presentation',
        'ps': 'print',
        'psd': 'image',
        'psp': 'image',
        'py': 'script',
        'r': 'script',
        'ra': 'audio',
        'rar': 'archive',
        'rb': 'script',
        'rpm': 'archive',
        'rtf': 'text',
        'sh': 'script',
        'sub': 'disk',
        'svg': 'vector',
        'sxc': 'spreadsheet',
        'sxd': 'vector',
        'tar': 'archive',
        'tga': 'image',
        'tif': 'image',
        'tiff': 'image',
        'ttf': 'font',
        'txt': 'text',
        'vbs': 'script',
        'vc': 'spreadsheet',
        'vml': 'vector',
        'wav': 'audio',
        'webp': 'image',
        'wma': 'audio',
        'wmv': 'video',
        'woff': 'font',
        'xar': 'vector',
        'xbm': 'image',
        'xcf': 'image',
        'xhtml': 'html',
        'xls': 'spreadsheet',
        'xlsx': 'spreadsheet',
        'xml': 'html',
        'zip': 'archive'
    }

    def get_attachment_type(self, cr, uid, ids, name, args, context=None):
        result = {}
        for attachment in self.browse(cr, uid, ids, context=context):
            fileext = os.path.splitext(attachment.datas_fname or '')[1].lower()[1:]
            result[attachment.id] = self._fileext_to_type.get(fileext, 'unknown')
        return result

    _columns = {
        'file_type_icon': fields.function(get_attachment_type, type='char', string='File Type Icon'),
        'file_type': fields.related('file_type_icon', type='char'),     # FIXME remove in trunk
    }
