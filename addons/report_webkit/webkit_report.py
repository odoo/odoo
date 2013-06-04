# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# All Right Reserved
#
# Author : Nicolas Bessi (Camptocamp)
# Contributor(s) : Florent Xicluna (Wingo SA)
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################

import subprocess
import os
import sys
from openerp import report
import tempfile
import time
import logging

from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

from openerp import netsvc
from openerp import pooler
from report_helper import WebKitHelper
from openerp.report.report_sxw import *
from openerp import addons
from openerp import tools
from openerp.tools.translate import _
from openerp.osv.osv import except_osv

_logger = logging.getLogger(__name__)

def mako_template(text):
    """Build a Mako template.

    This template uses UTF-8 encoding
    """
    tmp_lookup  = TemplateLookup() #we need it in order to allow inclusion and inheritance
    return Template(text, input_encoding='utf-8', output_encoding='utf-8', lookup=tmp_lookup)

class WebKitParser(report_sxw):
    """Custom class that use webkit to render HTML reports
       Code partially taken from report openoffice. Thanks guys :)
    """
    def __init__(self, name, table, rml=False, parser=False,
        header=True, store=False):
        self.parser_instance = False
        self.localcontext = {}
        report_sxw.__init__(self, name, table, rml, parser,
            header, store)

    def get_lib(self, cursor, uid):
        """Return the lib wkhtml path"""
        proxy = self.pool.get('ir.config_parameter')
        webkit_path = proxy.get_param(cursor, uid, 'webkit_path')

        if not webkit_path:
            try:
                defpath = os.environ.get('PATH', os.defpath).split(os.pathsep)
                if hasattr(sys, 'frozen'):
                    defpath.append(os.getcwd())
                    if tools.config['root_path']:
                        defpath.append(os.path.dirname(tools.config['root_path']))
                webkit_path = tools.which('wkhtmltopdf', path=os.pathsep.join(defpath))
            except IOError:
                webkit_path = None

        if webkit_path:
            return webkit_path

        raise except_osv(
                         _('Wkhtmltopdf library path is not set'),
                         _('Please install executable on your system' \
                         ' (sudo apt-get install wkhtmltopdf) or download it from here:' \
                         ' http://code.google.com/p/wkhtmltopdf/downloads/list and set the' \
                         ' path in the ir.config_parameter with the webkit_path key.' \
                         'Minimal version is 0.9.9')
                        )

    def generate_pdf(self, comm_path, report_xml, header, footer, html_list, webkit_header=False):
        """Call webkit in order to generate pdf"""
        if not webkit_header:
            webkit_header = report_xml.webkit_header
        tmp_dir = tempfile.gettempdir()
        out_filename = tempfile.mktemp(suffix=".pdf", prefix="webkit.tmp.")
        file_to_del = [out_filename]
        if comm_path:
            command = [comm_path]
        else:
            command = ['wkhtmltopdf']

        command.append('--quiet')
        # default to UTF-8 encoding.  Use <meta charset="latin-1"> to override.
        command.extend(['--encoding', 'utf-8'])
        if header :
            head_file = file( os.path.join(
                                  tmp_dir,
                                  str(time.time()) + '.head.html'
                                 ),
                                'w'
                            )
            head_file.write(header)
            head_file.close()
            file_to_del.append(head_file.name)
            command.extend(['--header-html', head_file.name])
        if footer :
            foot_file = file(  os.path.join(
                                  tmp_dir,
                                  str(time.time()) + '.foot.html'
                                 ),
                                'w'
                            )
            foot_file.write(footer)
            foot_file.close()
            file_to_del.append(foot_file.name)
            command.extend(['--footer-html', foot_file.name])

        if webkit_header.margin_top :
            command.extend(['--margin-top', str(webkit_header.margin_top).replace(',', '.')])
        if webkit_header.margin_bottom :
            command.extend(['--margin-bottom', str(webkit_header.margin_bottom).replace(',', '.')])
        if webkit_header.margin_left :
            command.extend(['--margin-left', str(webkit_header.margin_left).replace(',', '.')])
        if webkit_header.margin_right :
            command.extend(['--margin-right', str(webkit_header.margin_right).replace(',', '.')])
        if webkit_header.orientation :
            command.extend(['--orientation', str(webkit_header.orientation).replace(',', '.')])
        if webkit_header.format :
            command.extend(['--page-size', str(webkit_header.format).replace(',', '.')])
        count = 0
        for html in html_list :
            html_file = file(os.path.join(tmp_dir, str(time.time()) + str(count) +'.body.html'), 'w')
            count += 1
            html_file.write(html)
            html_file.close()
            file_to_del.append(html_file.name)
            command.append(html_file.name)
        command.append(out_filename)
        stderr_fd, stderr_path = tempfile.mkstemp(text=True)
        file_to_del.append(stderr_path)
        try:
            status = subprocess.call(command, stderr=stderr_fd)
            os.close(stderr_fd) # ensure flush before reading
            stderr_fd = None # avoid closing again in finally block
            fobj = open(stderr_path, 'r')
            error_message = fobj.read()
            fobj.close()
            if not error_message:
                error_message = _('No diagnosis message was provided')
            else:
                error_message = _('The following diagnosis message was provided:\n') + error_message
            if status :
                raise except_osv(_('Webkit error' ),
                                 _("The command 'wkhtmltopdf' failed with error code = %s. Message: %s") % (status, error_message))
            pdf_file = open(out_filename, 'rb')
            pdf = pdf_file.read()
            pdf_file.close()
        finally:
            if stderr_fd is not None:
                os.close(stderr_fd)
            for f_to_del in file_to_del:
                try:
                    os.unlink(f_to_del)
                except (OSError, IOError), exc:
                    _logger.error('cannot remove file %s: %s', f_to_del, exc)
        return pdf

    def translate_call(self, src):
        """Translate String."""
        ir_translation = self.pool.get('ir.translation')
        res = ir_translation._get_source(self.parser_instance.cr, self.parser_instance.uid,
                                         None, 'report', self.parser_instance.localcontext.get('lang', 'en_US'), src)
        if not res :
            return src
        return res

    # override needed to keep the attachments storing procedure
    def create_single_pdf(self, cursor, uid, ids, data, report_xml, context=None):
        """generate the PDF"""

        if context is None:
            context={}
        htmls = []
        if report_xml.report_type != 'webkit':
            return super(WebKitParser,self).create_single_pdf(cursor, uid, ids, data, report_xml, context=context)

        self.parser_instance = self.parser(cursor,
                                           uid,
                                           self.name2,
                                           context=context)

        self.pool = pooler.get_pool(cursor.dbname)
        objs = self.getObjects(cursor, uid, ids, context)
        self.parser_instance.set_context(objs, data, ids, report_xml.report_type)

        template =  False

        if report_xml.report_file :
            # backward-compatible if path in Windows format
            report_path = report_xml.report_file.replace("\\", "/")
            path = addons.get_module_resource(*report_path.split('/'))
            if path and os.path.exists(path) :
                template = file(path).read()
        if not template and report_xml.report_webkit_data :
            template =  report_xml.report_webkit_data
        if not template :
            raise except_osv(_('Error!'), _('Webkit report template not found!'))
        header = report_xml.webkit_header.html
        footer = report_xml.webkit_header.footer_html
        if not header and report_xml.header:
            raise except_osv(
                  _('No header defined for this Webkit report!'),
                  _('Please set a header in company settings.')
              )
        if not report_xml.header :
            header = ''
            default_head = addons.get_module_resource('report_webkit', 'default_header.html')
            with open(default_head,'r') as f:
                header = f.read()
        css = report_xml.webkit_header.css
        if not css :
            css = ''

        #default_filters=['unicode', 'entity'] can be used to set global filter
        body_mako_tpl = mako_template(template)
        helper = WebKitHelper(cursor, uid, report_xml.id, context)
        if report_xml.precise_mode:
            for obj in objs:
                self.parser_instance.localcontext['objects'] = [obj]
                try :
                    html = body_mako_tpl.render(helper=helper,
                                                css=css,
                                                _=self.translate_call,
                                                **self.parser_instance.localcontext)
                    htmls.append(html)
                except Exception:
                    msg = exceptions.text_error_template().render()
                    _logger.error(msg)
                    raise except_osv(_('Webkit render!'), msg)
        else:
            try :
                html = body_mako_tpl.render(helper=helper,
                                            css=css,
                                            _=self.translate_call,
                                            **self.parser_instance.localcontext)
                htmls.append(html)
            except Exception:
                msg = exceptions.text_error_template().render()
                _logger.error(msg)
                raise except_osv(_('Webkit render!'), msg)
        head_mako_tpl = mako_template(header)
        try :
            head = head_mako_tpl.render(helper=helper,
                                        css=css,
                                        _=self.translate_call,
                                        _debug=False,
                                        **self.parser_instance.localcontext)
        except Exception:
            raise except_osv(_('Webkit render!'),
                exceptions.text_error_template().render())
        foot = False
        if footer :
            foot_mako_tpl = mako_template(footer)
            try :
                foot = foot_mako_tpl.render(helper=helper,
                                            css=css,
                                            _=self.translate_call,
                                            **self.parser_instance.localcontext)
            except:
                msg = exceptions.text_error_template().render()
                _logger.error(msg)
                raise except_osv(_('Webkit render!'), msg)
        if report_xml.webkit_debug :
            try :
                deb = head_mako_tpl.render(helper=helper,
                                           css=css,
                                           _debug=tools.ustr("\n".join(htmls)),
                                           _=self.translate_call,
                                           **self.parser_instance.localcontext)
            except Exception:
                msg = exceptions.text_error_template().render()
                _logger.error(msg)
                raise except_osv(_('Webkit render!'), msg)
            return (deb, 'html')
        bin = self.get_lib(cursor, uid)
        pdf = self.generate_pdf(bin, report_xml, head, foot, htmls)
        return (pdf, 'pdf')


    def create(self, cursor, uid, ids, data, context=None):
        """We override the create function in order to handle generator
           Code taken from report openoffice. Thanks guys :) """
        pool = pooler.get_pool(cursor.dbname)
        ir_obj = pool.get('ir.actions.report.xml')
        report_xml_ids = ir_obj.search(cursor, uid,
                [('report_name', '=', self.name[7:])], context=context)
        if report_xml_ids:

            report_xml = ir_obj.browse(cursor,
                                       uid,
                                       report_xml_ids[0],
                                       context=context)
            report_xml.report_rml = None
            report_xml.report_rml_content = None
            report_xml.report_sxw_content_data = None
            report_xml.report_sxw_content = None
            report_xml.report_sxw = None
        else:
            return super(WebKitParser, self).create(cursor, uid, ids, data, context)
        if report_xml.report_type != 'webkit' :
            return super(WebKitParser, self).create(cursor, uid, ids, data, context)
        result = self.create_source_pdf(cursor, uid, ids, data, report_xml, context)
        if not result:
            return (False,False)
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
