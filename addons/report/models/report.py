# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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

from openerp.osv import osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, config
from openerp.osv.fields import float as float_field, function as function_field, datetime as datetime_field

import os
import time
import psutil
import signal
import base64
import logging
import tempfile
import lxml.html
import cStringIO
import subprocess
from datetime import datetime
from distutils.version import LooseVersion
try:
    from pyPdf import PdfFileWriter, PdfFileReader
except ImportError:
    PdfFileWriter = PdfFileReader = None


_logger = logging.getLogger(__name__)


class Report(osv.Model):
    _name = "report"
    _description = "Report"

    public_user = None

    #--------------------------------------------------------------------------
    # Extension of ir_ui_view.render with arguments frequently used in reports
    #--------------------------------------------------------------------------

    def get_digits(self, cr, uid, obj=None, f=None, dp=None):
        d = DEFAULT_DIGITS = 2
        if dp:
            decimal_precision_obj = self.pool['decimal.precision']
            ids = decimal_precision_obj.search(cr, uid, [('name', '=', dp)])
            if ids:
                d = decimal_precision_obj.browse(cr, uid, ids)[0].digits
        elif obj and f:
            res_digits = getattr(obj._columns[f], 'digits', lambda x: ((16, DEFAULT_DIGITS)))
            if isinstance(res_digits, tuple):
                d = res_digits[1]
            else:
                d = res_digits(cr)[1]
        elif (hasattr(obj, '_field') and
                isinstance(obj._field, (float_field, function_field)) and
                obj._field.digits):
                d = obj._field.digits[1] or DEFAULT_DIGITS
        return d

    def _get_lang_dict(self, cr, uid):
        pool_lang = self.pool['res.lang']
        lang = self.localcontext.get('lang', 'en_US') or 'en_US'
        lang_ids = pool_lang.search(cr, uid, [('code', '=', lang)])[0]
        lang_obj = pool_lang.browse(cr, uid, lang_ids)
        lang_dict = {
            'lang_obj': lang_obj,
            'date_format': lang_obj.date_format,
            'time_format': lang_obj.time_format
        }
        self.lang_dict.update(lang_dict)
        self.default_lang[lang] = self.lang_dict.copy()
        return True

    def formatLang(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False, cr=None, uid=None):
        """
            Assuming 'Account' decimal.precision=3:
                formatLang(value) -> digits=2 (default)
                formatLang(value, digits=4) -> digits=4
                formatLang(value, dp='Account') -> digits=3
                formatLang(value, digits=5, dp='Account') -> digits=5
        """
        def get_date_length(date_format=DEFAULT_SERVER_DATE_FORMAT):
            return len((datetime.now()).strftime(date_format))

        if digits is None:
            if dp:
                digits = self.get_digits(cr, uid, dp=dp)
            else:
                digits = self.get_digits(cr, uid, value)

        if isinstance(value, (str, unicode)) and not value:
            return ''

        if not self.lang_dict_called:
            self._get_lang_dict(cr, uid)
            self.lang_dict_called = True

        if date or date_time:
            if not str(value):
                return ''

            date_format = self.lang_dict['date_format']
            parse_format = DEFAULT_SERVER_DATE_FORMAT
            if date_time:
                value = value.split('.')[0]
                date_format = date_format + " " + self.lang_dict['time_format']
                parse_format = DEFAULT_SERVER_DATETIME_FORMAT
            if isinstance(value, basestring):
                # FIXME: the trimming is probably unreliable if format includes day/month names
                #        and those would need to be translated anyway.
                date = datetime.strptime(value[:get_date_length(parse_format)], parse_format)
            elif isinstance(value, time.struct_time):
                date = datetime(*value[:6])
            else:
                date = datetime(*value.timetuple()[:6])
            if date_time:
                # Convert datetime values to the expected client/context timezone
                date = datetime_field.context_timestamp(cr, uid, timestamp=date, context=self.localcontext)
            return date.strftime(date_format.encode('utf-8'))

        res = self.lang_dict['lang_obj'].format('%.' + str(digits) + 'f', value, grouping=grouping, monetary=monetary)
        if currency_obj:
            if currency_obj.position == 'after':
                res = '%s %s' % (res, currency_obj.symbol)
            elif currency_obj and currency_obj.position == 'before':
                res = '%s %s' % (currency_obj.symbol, res)
        return res

    def render(self, cr, uid, ids, template, values=None, context=None):
        """Allow to render a QWeb template python-side. This function returns the 'ir.ui.view'
        render but embellish it with some variables/methods used in reports.

        :param values: additionnal methods/variables used in the rendering
        :returns: html representation of the template
        """
        if values is None:
            values = {}

        if context is None:
            context = {}

        self.lang_dict = self.default_lang = {}
        self.lang_dict_called = False
        self.localcontext = {
            'lang': context.get('lang'),
            'tz': context.get('tz'),
            'uid': context.get('uid'),
        }
        self._get_lang_dict(cr, uid)

        view_obj = self.pool['ir.ui.view']

        def render_doc(doc_id, model, template):
            """Helper used when a report should be translated into the associated
            partner's lang.

            <t t-foreach="doc_ids" t-as="doc_id">
                <t t-raw="render_doc(doc_id, doc_model, 'module.templatetocall')"/>
            </t>

            :param doc_id: id of the record to translate
            :param model: model of the record to translate
            :param template: name of the template to translate into the partner's lang
            """
            ctx = context.copy()
            doc = self.pool[model].browse(cr, uid, doc_id, context=ctx)
            qcontext = values.copy()
            # Do not force-translate if we chose to display the report in a specific lang
            if ctx.get('translatable') is True:
                qcontext['o'] = doc
            else:
                ctx['lang'] = doc.partner_id.lang
                qcontext['o'] = self.pool[model].browse(cr, uid, doc_id, context=ctx)
            return view_obj.render(cr, uid, template, qcontext, context=ctx)

        values.update({
            'time': time,
            'formatLang': lambda *args, **kwargs: self.formatLang(*args, cr=cr, uid=uid, **kwargs),
            'get_digits': self.get_digits,
            'render_doc': render_doc,
            'editable': True,  # Will active inherit_branding
            'res_company': self.pool['res.users'].browse(cr, uid, uid).company_id
        })

        return view_obj.render(cr, uid, template, values, context=context)

    #--------------------------------------------------------------------------
    # Main reports methods
    #--------------------------------------------------------------------------

    def get_html(self, cr, uid, ids, report_name, data=None, context=None):
        """This method generates and returns html version of a report.
        """
        if context is None:
            context = {}

        if isinstance(ids, (str, unicode)):
            ids = [int(i) for i in ids.split(',')]
        if isinstance(ids, list):
            ids = list(set(ids))
        if isinstance(ids, int):
            ids = [ids]

        # If the report is using a custom model to render its html, we must use it.
        # Otherwise, fallback on the generic html rendering.
        try:
            report_model_name = 'report.%s' % report_name
            particularreport_obj = self.pool[report_model_name]
            return particularreport_obj.render_html(cr, uid, ids, data=data, context=context)
        except:
            pass

        report = self._get_report_from_name(cr, uid, report_name)
        report_obj = self.pool[report.model]
        docs = report_obj.browse(cr, uid, ids, context=context)

        docargs = {
            'doc_ids': ids,
            'doc_model': report.model,
            'docs': docs,
        }
        return self.render(cr, uid, [], report.report_name, docargs, context=context)

    def get_pdf(self, cr, uid, ids, report_name, html=None, data=None, context=None):
        """This method generates and returns pdf version of a report.
        """
        if context is None:
            context = {}

        if isinstance(ids, (str, unicode)):
            ids = [int(i) for i in ids.split(',')]
        if isinstance(ids, list):
            ids = list(set(ids))
        if isinstance(ids, int):
            ids = [ids]

        if html is None:
            html = self.get_html(cr, uid, ids, report_name, data=data, context=context)

        html = html.decode('utf-8')

        # Get the ir.actions.report.xml record we are working on.
        report = self._get_report_from_name(cr, uid, report_name)

        # Check attachment_use field. If set to true and an existing pdf is already saved, load
        # this one now. If not, mark save it.
        save_in_attachment = {}

        if report.attachment_use is True:
            save_in_attachment['model'] = report.model
            save_in_attachment['loaded_documents'] = {}

            for record_id in ids:
                obj = self.pool[report.model].browse(cr, uid, record_id)
                filename = eval(report.attachment, {'object': obj, 'time': time})

                if filename is False:  # May be false if, for instance, the record is in draft state
                    continue
                else:
                    alreadyindb = [('datas_fname', '=', filename),
                                   ('res_model', '=', report.model),
                                   ('res_id', '=', record_id)]

                    attach_ids = self.pool['ir.attachment'].search(cr, uid, alreadyindb)
                    if attach_ids:
                        # Add the loaded pdf in the loaded_documents list
                        pdf = self.pool['ir.attachment'].browse(cr, uid, attach_ids[0]).datas
                        pdf = base64.decodestring(pdf)
                        save_in_attachment['loaded_documents'][record_id] = pdf
                        _logger.info('The PDF document %s was loaded from the database' % filename)
                    else:
                        # Mark current document to be saved
                        save_in_attachment[id] = filename

        # Get the paperformat associated to the report, otherwise fallback on the company one.
        if not report.paperformat_id:
            user = self.pool['res.users'].browse(cr, uid, uid)
            paperformat = user.company_id.paperformat_id
        else:
            paperformat = report.paperformat_id

        # Preparing the minimal html pages
        #subst = self._get_url_content('/report/static/src/js/subst.js')[0]  # Used in age numbering
        subst = "<script src='/report/static/src/js/subst.js'></script> "
        css = ''  # Will contain local css

        headerhtml = []
        contenthtml = []
        footerhtml = []
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')

        minimalhtml = """
<base href="{3}">
<!DOCTYPE html>
<html style="height: 0;">
    <head>
        <link href="/report/static/src/css/reset.min.css" rel="stylesheet"/>
        <link href="/web/static/lib/bootstrap/css/bootstrap.css" rel="stylesheet"/>
        <link href="/website/static/src/css/website.css" rel="stylesheet"/>
        <link href="/web/static/lib/fontawesome/css/font-awesome.css" rel="stylesheet"/>
        <style type='text/css'>{0}</style>
        {1}
    </head>
    <body class="container" onload='subst()'>
        {2}
    </body>
</html>"""

        # The retrieved html report must be simplified. We convert it into a xml tree
        # via lxml in order to extract headers, footers and content.
        try:
            root = lxml.html.fromstring(html)

            for node in root.xpath("//html/head/style"):
                css += node.text

            for node in root.xpath("//div[@class='header']"):
                body = lxml.html.tostring(node)
                header = minimalhtml.format(css, subst, body, base_url)
                headerhtml.append(header)

            for node in root.xpath("//div[@class='footer']"):
                body = lxml.html.tostring(node)
                footer = minimalhtml.format(css, subst, body, base_url)
                footerhtml.append(footer)

            for node in root.xpath("//div[@class='page']"):
                # Previously, we marked some reports to be saved in attachment via their ids, so we
                # must set a relation between report ids and report's content. We use the QWeb
                # branding in order to do so: searching after a node having a data-oe-model
                # attribute with the value of the current report model and read its oe-id attribute
                oemodelnode = node.find(".//*[@data-oe-model='" + report.model + "']")
                if oemodelnode is not None:
                    reportid = oemodelnode.get('data-oe-id', False)
                    if reportid is not False:
                        reportid = int(reportid)
                else:
                    reportid = False

                body = lxml.html.tostring(node)
                reportcontent = minimalhtml.format(css, '', body, base_url)
                contenthtml.append(tuple([reportid, reportcontent]))

        except lxml.etree.XMLSyntaxError:
            contenthtml = []
            contenthtml.append(html)
            save_in_attachment = {}  # Don't save this potentially malformed document

        # Get paperformat arguments set in the root html tag. They are prioritized over
        # paperformat-record arguments.
        specific_paperformat_args = {}
        for attribute in root.items():
            if attribute[0].startswith('data-report-'):
                specific_paperformat_args[attribute[0]] = attribute[1]

        # Run wkhtmltopdf process
        pdf = self._generate_wkhtml_pdf(
            cr, uid, headerhtml, footerhtml, contenthtml, context.get('landscape'),
            paperformat, specific_paperformat_args, save_in_attachment
        )
        return pdf

    def get_action(self, cr, uid, ids, report_name, datas=None, context=None):
        """Return an action of type ir.actions.report.xml.

        :param report_name: Name of the template to generate an action for
        """
        # TODO: return the action for the ids passed in args
        if context is None:
            context = {}

        if datas is None:
            datas = {}

        report_obj = self.pool.get('ir.actions.report.xml')
        idreport = report_obj.search(cr, uid, [('report_name', '=', report_name)], context=context)

        try:
            report = report_obj.browse(cr, uid, idreport[0], context=context)
        except IndexError:
            raise osv.except_osv(_('Bad Report'),
                                 _('This report is not loaded into the database.'))

        action = {
            'type': 'ir.actions.report.xml',
            'report_name': report.report_name,
            'report_type': report.report_type,
            'report_file': report.report_file,
        }

        if datas:
            action['datas'] = datas

        return action

    #--------------------------------------------------------------------------
    # Report generation helpers
    #--------------------------------------------------------------------------

    def check_wkhtmltopdf(self):
        """Check the presence of wkhtmltopdf and return its version. If wkhtmltopdf
        cannot be found, return False.
        """
        try:
            process = subprocess.Popen(['wkhtmltopdf', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()
            if err:
                raise

            version = out.splitlines()[1].strip()
            version = version.split(' ')[1]

            if LooseVersion(version) < LooseVersion('0.12.0'):
                _logger.warning('Upgrade WKHTMLTOPDF to (at least) 0.12.0')
                return 'upgrade'

            return True
        except:
            _logger.error('You need WKHTMLTOPDF to print a pdf version of this report.')
            return False

    def _generate_wkhtml_pdf(self, cr, uid, headers, footers, bodies, landscape, paperformat, spec_paperformat_args=None, save_in_attachment=None):
        """Execute wkhtmltopdf as a subprocess in order to convert html given in input into a pdf
        document.

        :param header: list of string containing the headers
        :param footer: list of string containing the footers
        :param bodies: list of string containing the reports
        :param landscape: boolean to force the pdf to be rendered under a landscape format
        :param paperformat: ir.actions.report.paperformat to generate the wkhtmltopf arguments
        :param specific_paperformat_args: dict of prioritized paperformat arguments
        :param save_in_attachment: dict of reports to save/load in/from the db
        :returns: Content of the pdf as a string
        """
        command = ['wkhtmltopdf']
        tmp_dir = tempfile.gettempdir()

        command_args = []
        # Passing the cookie to wkhtmltopdf in order to resolve URL.
        try:
            from openerp.addons.web.http import request
            command_args.extend(['--cookie', 'session_id', request.httprequest.cookies['session_id']])
        except:
            pass

        # Display arguments
        if paperformat:
            command_args.extend(self._build_wkhtmltopdf_args(paperformat, spec_paperformat_args))

        if landscape and '--orientation' in command_args:
            command_args_copy = list(command_args)
            for index, elem in enumerate(command_args_copy):
                if elem == '--orientation':
                    del command_args[index]
                    del command_args[index]
                    command_args.extend(['--orientation', 'landscape'])
        elif landscape and not '--orientation' in command_args:
            command_args.extend(['--orientation', 'landscape'])

        pdfdocuments = []
        # HTML to PDF thanks to WKhtmltopdf
        for index, reporthtml in enumerate(bodies):
            command_arg_local = []
            pdfreport = tempfile.NamedTemporaryFile(suffix='.pdf', prefix='report.tmp.',
                                                    mode='w+b')
            # Directly load the document if we have it
            if save_in_attachment and save_in_attachment['loaded_documents'].get(reporthtml[0]):
                pdfreport.write(save_in_attachment['loaded_documents'].get(reporthtml[0]))
                pdfreport.flush()
                pdfdocuments.append(pdfreport)
                continue

            # Header stuff
            if headers:
                head_file = tempfile.NamedTemporaryFile(suffix='.html', prefix='report.header.tmp.',
                                                        dir=tmp_dir, mode='w+')
                head_file.write(headers[index])
                head_file.flush()
                command_arg_local.extend(['--header-html', head_file.name])

            # Footer stuff
            if footers:
                foot_file = tempfile.NamedTemporaryFile(suffix='.html', prefix='report.footer.tmp.',
                                                        dir=tmp_dir, mode='w+')
                foot_file.write(footers[index])
                foot_file.flush()
                command_arg_local.extend(['--footer-html', foot_file.name])

            # Body stuff
            content_file = tempfile.NamedTemporaryFile(suffix='.html', prefix='report.body.tmp.',
                                                       dir=tmp_dir, mode='w+')
            content_file.write(reporthtml[1])
            content_file.flush()

            try:
                # If the server is running with only one worker, increase it to two to be able
                # to serve the http request from wkhtmltopdf.
                if config['workers'] == 1:
                    ppid = psutil.Process(os.getpid()).ppid
                    os.kill(ppid, signal.SIGTTIN)

                wkhtmltopdf = command + command_args + command_arg_local
                wkhtmltopdf += [content_file.name] + [pdfreport.name]

                process = subprocess.Popen(wkhtmltopdf, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                out, err = process.communicate()

                if config['workers'] == 1:
                    os.kill(ppid, signal.SIGTTOU)

                if process.returncode != 0:
                    raise osv.except_osv(_('Report (PDF)'),
                                         _('wkhtmltopdf failed with error code = %s. '
                                           'Message: %s') % (str(process.returncode), err))

                # Save the pdf in attachment if marked
                if reporthtml[0] is not False and save_in_attachment.get(reporthtml[0]):
                    attachment = {
                        'name': save_in_attachment.get(reporthtml[0]),
                        'datas': base64.encodestring(pdfreport.read()),
                        'datas_fname': save_in_attachment.get(reporthtml[0]),
                        'res_model': save_in_attachment.get('model'),
                        'res_id': reporthtml[0],
                    }
                    self.pool['ir.attachment'].create(cr, uid, attachment)
                    _logger.info('The PDF document %s is now saved in the '
                                 'database' % attachment['name'])

                pdfreport.flush()
                pdfdocuments.append(pdfreport)

                if headers:
                    head_file.close()
                if footers:
                    foot_file.close()
            except:
                raise

        # Get and return the full pdf
        if len(pdfdocuments) == 1:
            content = pdfdocuments[0].read()
            pdfdocuments[0].close()
        else:
            content = self._merge_pdf(pdfdocuments)

        return content

    def _get_report_from_name(self, cr, uid, report_name):
        """Get the first record of ir.actions.report.xml having the ``report_name`` as value for
        the field report_name.
        """
        report_obj = self.pool['ir.actions.report.xml']
        qwebtypes = ['qweb-pdf', 'qweb-html']
        conditions = [('report_type', 'in', qwebtypes), ('report_name', '=', report_name)]
        idreport = report_obj.search(cr, uid, conditions)[0]
        return report_obj.browse(cr, uid, idreport)

    def _build_wkhtmltopdf_args(self, paperformat, specific_paperformat_args=None):
        """Build arguments understandable by wkhtmltopdf from a report.paperformat record.

        :paperformat: report.paperformat record
        :specific_paperformat_args: a dict containing prioritized wkhtmltopdf arguments
        :returns: list of string representing the wkhtmltopdf arguments
        """
        command_args = []
        if paperformat.format and paperformat.format != 'custom':
            command_args.extend(['--page-size', paperformat.format])

        if paperformat.page_height and paperformat.page_width and paperformat.format == 'custom':
            command_args.extend(['--page-width', str(paperformat.page_width) + 'in'])
            command_args.extend(['--page-height', str(paperformat.page_height) + 'in'])

        if specific_paperformat_args and specific_paperformat_args['data-report-margin-top']:
            command_args.extend(['--margin-top',
                                 str(specific_paperformat_args['data-report-margin-top'])])
        elif paperformat.margin_top:
            command_args.extend(['--margin-top', str(paperformat.margin_top)])

        if paperformat.margin_left:
            command_args.extend(['--margin-left', str(paperformat.margin_left)])
        if paperformat.margin_bottom:
            command_args.extend(['--margin-bottom', str(paperformat.margin_bottom)])
        if paperformat.margin_right:
            command_args.extend(['--margin-right', str(paperformat.margin_right)])
        if paperformat.orientation:
            command_args.extend(['--orientation', str(paperformat.orientation)])
        if paperformat.header_spacing:
            command_args.extend(['--header-spacing', str(paperformat.header_spacing)])
        if paperformat.header_line:
            command_args.extend(['--header-line'])
        if paperformat.dpi:
            command_args.extend(['--dpi', str(paperformat.dpi)])

        return command_args

    def _merge_pdf(self, documents):
        """Merge PDF files into one.

        :param documents: list of pdf files
        :returns: string containing the merged pdf
        """
        writer = PdfFileWriter()
        for document in documents:
            reader = PdfFileReader(file(document.name, "rb"))
            for page in range(0, reader.getNumPages()):
                writer.addPage(reader.getPage(page))
            document.close()
        merged = cStringIO.StringIO()
        writer.write(merged)
        merged.seek(0)
        content = merged.read()
        merged.close()
        return content

    def eval_params(self, dict_param):
        """Parse a dict generated by the webclient (javascript) into a python dict.
        """
        for key, value in dict_param.iteritems():
            if value.lower() == 'false':
                dict_param[key] = False
            elif value.lower() == 'true':
                dict_param[key] = True
            elif ',' in value:
                dict_param[key] = [int(i) for i in value.split(',')]
            elif '%2C' in value:
                dict_param[key] = [int(i) for i in value.split('%2C')]
            else:
                try:
                    i = int(value)
                    dict_param[key] = i
                except (ValueError, TypeError):
                    pass

        data = {}
        data['form'] = dict_param
        return data
