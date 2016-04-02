# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# Author : Nicolas Bessi (Camptocamp)
# Contributor(s) : Florent Xicluna (Wingo SA)

import subprocess
import os
import sys
from openerp import report
import tempfile
import time
import logging
from functools import partial

from report_helper import WebKitHelper
import openerp
from openerp.modules.module import get_module_resource
from openerp.report.report_sxw import *
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from urllib import urlencode, quote as quote
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    mako_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,               # do not output newline after blocks
        autoescape=True,                # XML/HTML automatic escaping
    )
    mako_template_env.globals.update({
        'str': str,
        'quote': quote,
        'urlencode': urlencode,
    })
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")

def mako_template(text):
    """Build a Mako template.

    This template uses UTF-8 encoding
    """

    return mako_template_env.from_string(text)

_extender_functions = {}

def webkit_report_extender(report_name):
    """
    A decorator to define functions to extend the context used in a template rendering.
    report_name must be the xml id of the desired report (it is mandatory to indicate the
    module in that xml id).

    The given function will be called at the creation of the report. The following arguments
    will be passed to it (in this order):
    - pool The model pool.
    - cr The cursor.
    - uid The user id.
    - localcontext The context given to the template engine to render the templates for the
        current report. This is the context that should be modified.
    - context The OpenERP context.
    """
    def fct1(fct):
        lst = _extender_functions.get(report_name)
        if not lst:
            lst = []
            _extender_functions[report_name] = lst
        lst.append(fct)
        return fct
    return fct1


class WebKitParser(report_sxw):
    """Custom class that use webkit to render HTML reports
       Code partially taken from report openoffice. Thanks guys :)
    """
    def __init__(self, name, table, rml=False, parser=rml_parse,
        header=True, store=False, register=True):
        self.localcontext = {}
        report_sxw.__init__(self, name, table, rml, parser,
            header, store, register=register)

    def get_lib(self, cursor, uid):
        """Return the lib wkhtml path"""
        proxy = self.pool['ir.config_parameter']
        webkit_path = proxy.get_param(cursor, SUPERUSER_ID, 'webkit_path')

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

        raise UserError(_('Wkhtmltopdf library path is not set') + ' ' +
                            _('Please install executable on your system'
                            ' (sudo apt-get install wkhtmltopdf) or download it from here:'
                            ' http://code.google.com/p/wkhtmltopdf/downloads/list and set the'
                            ' path in the ir.config_parameter with the webkit_path key.'
                            'Minimal version is 0.9.9'))

    def generate_pdf(self, comm_path, report_xml, header, footer, html_list, webkit_header=False):
        """Call webkit in order to generate pdf"""
        if not webkit_header:
            webkit_header = report_xml.webkit_header
        fd, out_filename = tempfile.mkstemp(suffix=".pdf",
                                            prefix="webkit.tmp.")
        file_to_del = [out_filename]
        if comm_path:
            command = [comm_path]
        else:
            command = ['wkhtmltopdf']

        command.append('--quiet')
        # default to UTF-8 encoding.  Use <meta charset="latin-1"> to override.
        command.extend(['--encoding', 'utf-8'])
        if header :
            with tempfile.NamedTemporaryFile(suffix=".head.html",
                                             delete=False) as head_file:
                head_file.write(self._sanitize_html(header.encode('utf-8')))
            file_to_del.append(head_file.name)
            command.extend(['--header-html', head_file.name])
        if footer :
            with tempfile.NamedTemporaryFile(suffix=".foot.html",
                                             delete=False) as foot_file:
                foot_file.write(self._sanitize_html(footer.encode('utf-8')))
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
            with tempfile.NamedTemporaryFile(suffix="%d.body.html" %count,
                                             delete=False) as html_file:
                count += 1
                html_file.write(self._sanitize_html(html.encode('utf-8')))
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
                raise UserError(_("The command 'wkhtmltopdf' failed with error code = %s. Message: %s") % (status, error_message))
            with open(out_filename, 'rb') as pdf_file:
                pdf = pdf_file.read()
            os.close(fd)
        finally:
            if stderr_fd is not None:
                os.close(stderr_fd)
            for f_to_del in file_to_del:
                try:
                    os.unlink(f_to_del)
                except (OSError, IOError), exc:
                    _logger.error('cannot remove file %s: %s', f_to_del, exc)
        return pdf

    def translate_call(self, parser_instance, src):
        """Translate String."""
        ir_translation = self.pool['ir.translation']
        name = self.tmpl and 'addons/' + self.tmpl or None
        res = ir_translation._get_source(parser_instance.cr, parser_instance.uid,
                                         name, 'report', parser_instance.localcontext.get('lang', 'en_US'), src)
        if res == src:
            # no translation defined, fallback on None (backward compatibility)
            res = ir_translation._get_source(parser_instance.cr, parser_instance.uid,
                                             None, 'report', parser_instance.localcontext.get('lang', 'en_US'), src)
        if not res :
            return src
        return res

    # override needed to keep the attachments storing procedure
    def create_single_pdf(self, cursor, uid, ids, data, report_xml, context=None):
        """generate the PDF"""

        # just try to find an xml id for the report
        cr = cursor
        pool = openerp.registry(cr.dbname)
        found_xml_ids = pool["ir.model.data"].search(cr, uid, [["model", "=", "ir.actions.report.xml"], \
            ["res_id", "=", report_xml.id]], context=context)
        xml_id = None
        if found_xml_ids:
            xml_id = pool["ir.model.data"].read(cr, uid, found_xml_ids[0], ["module", "name"])
            xml_id = "%s.%s" % (xml_id["module"], xml_id["name"])

        if context is None:
            context={}
        htmls = []
        if report_xml.report_type != 'webkit':
            return super(WebKitParser,self).create_single_pdf(cursor, uid, ids, data, report_xml, context=context)

        parser_instance = self.parser(cursor,
                                      uid,
                                      self.name2,
                                      context=context)

        self.pool = pool
        objs = self.getObjects(cursor, uid, ids, context)
        parser_instance.set_context(objs, data, ids, report_xml.report_type)

        template =  False

        if report_xml.report_file :
            path = get_module_resource(*report_xml.report_file.split('/'))
            if path and os.path.exists(path) :
                template = file(path).read()
        if not template and report_xml.report_webkit_data :
            template =  report_xml.report_webkit_data
        if not template :
            raise UserError(_('Webkit report template not found!'))
        header = report_xml.webkit_header.html
        footer = report_xml.webkit_header.footer_html
        if not header and report_xml.use_global_header:
            raise UserError(_('No header defined for this Webkit report!') + " " + _('Please set a header in company settings.'))
        if not report_xml.use_global_header :
            header = ''
            default_head = get_module_resource('report_webkit', 'default_header.html')
            with open(default_head,'r') as f:
                header = f.read()
        css = report_xml.webkit_header.css
        if not css :
            css = ''

        translate_call = partial(self.translate_call, parser_instance)
        body_mako_tpl = mako_template(template)
        helper = WebKitHelper(cursor, uid, report_xml.id, context)
        parser_instance.localcontext['helper'] = helper
        parser_instance.localcontext['css'] = css
        parser_instance.localcontext['_'] = translate_call

        # apply extender functions
        additional = {}
        if xml_id in _extender_functions:
            for fct in _extender_functions[xml_id]:
                fct(pool, cr, uid, parser_instance.localcontext, context)

        if report_xml.precise_mode:
            ctx = dict(parser_instance.localcontext)
            for obj in parser_instance.localcontext['objects']:
                ctx['objects'] = [obj]
                try :
                    html = body_mako_tpl.render(dict(ctx))
                    htmls.append(html)
                except Exception, e:
                    msg = u"%s" % e
                    _logger.info(msg, exc_info=True)
                    raise UserError(msg)
        else:
            try :
                html = body_mako_tpl.render(dict(parser_instance.localcontext))
                htmls.append(html)
            except Exception, e:
                msg = u"%s" % e
                _logger.info(msg, exc_info=True)
                raise UserError(msg)
        head_mako_tpl = mako_template(header)
        try :
            head = head_mako_tpl.render(dict(parser_instance.localcontext, _debug=False))
        except Exception, e:
            raise UserError(tools.ustr(e))
        foot = False
        if footer :
            foot_mako_tpl = mako_template(footer)
            try :
                foot = foot_mako_tpl.render(dict(parser_instance.localcontext))
            except Exception, e:
                msg = u"%s" % e
                _logger.info(msg, exc_info=True)
                raise UserError(msg)
        if report_xml.webkit_debug :
            try :
                deb = head_mako_tpl.render(dict(parser_instance.localcontext, _debug=tools.ustr("\n".join(htmls))))
            except Exception, e:
                msg = u"%s" % e
                _logger.info(msg, exc_info=True)
                raise UserError(msg)
            return (deb, 'html')
        bin = self.get_lib(cursor, uid)
        pdf = self.generate_pdf(bin, report_xml, head, foot, htmls)
        return (pdf, 'pdf')

    def create(self, cursor, uid, ids, data, context=None):
        """We override the create function in order to handle generator
           Code taken from report openoffice. Thanks guys :) """
        pool = openerp.registry(cursor.dbname)
        ir_obj = pool['ir.actions.report.xml']
        report_xml_ids = ir_obj.search(cursor, uid,
                [('report_name', '=', self.name[7:])], context=context)
        if report_xml_ids:
            report_xml = ir_obj.browse(cursor, uid, report_xml_ids[0], context=context)
        else:
            return super(WebKitParser, self).create(cursor, uid, ids, data, context)

        setattr(report_xml, 'use_global_header', self.header if report_xml.header else False)

        if report_xml.report_type != 'webkit':
            return super(WebKitParser, self).create(cursor, uid, ids, data, context)
        result = self.create_source_pdf(cursor, uid, ids, data, report_xml, context)
        if not result:
            return (False,False)
        return result

    def _sanitize_html(self, html):
        """wkhtmltopdf expects the html page to declare a doctype.
        """
        if html and html[:9].upper() != "<!DOCTYPE":
            html = "<!DOCTYPE html>\n" + html
        return html
