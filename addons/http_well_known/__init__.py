# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 OpenERP s.a. (<http://openerp.com>).
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
import tools
from service.websrv_lib import HTTPDir
from service.http_server import reg_http_service
from redirect import RedirectHTTPHandler

def init_well_known():
    reps = RedirectHTTPHandler.redirect_paths

    num_svcs = tools.config.get_misc('http-well-known', 'num_services', '0')

    for nsv in range(1, int(num_svcs)+1):
        uri = tools.config.get_misc('http-well-known', 'service_%d' % nsv, False)
        path = tools.config.get_misc('http-well-known', 'path_%d' % nsv, False)
        if not (uri and path):
            continue
        reps['/'+uri] = path

    if reg_http_service(HTTPDir('/.well-known', RedirectHTTPHandler)):
        logging.getLogger("web-services").info("Registered HTTP redirect handler at /.well-known" )


init_well_known()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
