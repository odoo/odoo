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

""" Helper functions for reports testing.

    Please /do not/ import this file by default, but only explicitly call it
    through the code of yaml tests.
"""

import netsvc
import tools
import logging
from subprocess import Popen, PIPE
import os
import tempfile

def try_report(cr, uid, rname, ids, data=None, context=None):
    """ Try to render a report <rname> with contents of ids
    
        This function should also check for common pitfalls of reports.
    """
    log = logging.getLogger('tools.test_reports')
    if data is None:
        data = {}
    if context is None:
        context = {}
    if rname.startswith('report.'):
        rname_s = rname[7:]
    else:
        rname_s = rname
    log.debug("Trying %s.create(%r)", rname, ids)
    res = netsvc.LocalService(rname).create(cr, uid, ids, data, context)
    if not isinstance(res, tuple):
        raise RuntimeError("Result of %s.create() should be a (data,format) tuple, now it is a %s" % \
                                (rname, type(res)))
    (res_data, res_format) = res
   
    if not res_data:
        raise ValueError("Report %s produced an empty result!" % rname)
    
    if tools.config['test_report_directory']:
        file(os.path.join(tools.config['test_report_directory'], rname+ '.'+res_format), 'wb+').write(res_data)

    log.debug("Have a %s report for %s, will examine it", res_format, rname)
    if res_format == 'pdf':
        if res_data[:5] != '%PDF-':
            raise ValueError("Report %s produced a non-pdf header, %r" % (rname, res_data[:10]))
    
        res_text = False
        try:
            fd, rfname = tempfile.mkstemp(suffix=res_format)
            os.write(fd, res_data)
            os.close(fd)

            fp = Popen(['pdftotext', '-enc', 'UTF-8', '-nopgbrk', rfname, '-'], shell=False, stdout=PIPE).stdout
            res_text = tools.ustr(fp.read())
            os.unlink(rfname)
        except Exception:
            log.warning("Cannot extract report's text:", exc_info=True)
        
        if res_text is not False:
            for line in res_text.split('\n'):
                if ('[[' in line) or ('[ [' in line):
                    log.error("Report %s may have bad expression near: \"%s\".", rname, line[80:])
            # TODO more checks, what else can be a sign of a faulty report?
    elif res_format == 'foobar':
        # TODO
        pass
    else:
        log.warning("Report %s produced a \"%s\" chunk, cannot examine it", rname, res_format)

    return True
#eof
