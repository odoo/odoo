# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
import tempfile
LOG_DEBUG='debug'
LOG_INFO='info'
LOG_WARNING='warn'
LOG_ERROR='error'
LOG_CRITICAL='critical'
_logger = logging.getLogger(__name__)

def log_detail(self):
    import os
    logfile_name = os.path.join(tempfile.gettempdir(), "openerp_report_designer.log")
    hdlr = logging.FileHandler(logfile_name)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    _logger.addHandler(hdlr)
    _logger.setLevel(logging.INFO)

class Logger(object):
    def log_write(self,name,level,msg):
        getattr(_logger,level)(msg)

    def shutdown(self):
        logging.shutdown()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
