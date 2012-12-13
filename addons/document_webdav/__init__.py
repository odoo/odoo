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

_logger = logging.getLogger(__name__)

try:
    import webdav
    import webdav_server
    import document_webdav
except ImportError:
    _logger.info('document_webdav disabled please install PyWebDAV from http://code.google.com/p/pywebdav/downloads/detail?name=PyWebDAV-0.9.4.tar.gz&can=2&q=/')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
