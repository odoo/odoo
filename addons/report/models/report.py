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

from openerp.addons.web.http import request
from openerp.osv import osv
from openerp.osv.fields import float as float_field, function as function_field, datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _

import time
from datetime import datetime

from werkzeug.datastructures import Headers
from werkzeug.wrappers import BaseResponse
from werkzeug.test import Client


def get_date_length(date_format=DEFAULT_SERVER_DATE_FORMAT):
    return len((datetime.now()).strftime(date_format))


class report(osv.Model):
    _name = "report"
    _description = "Report"

    public_user = None

    def get_digits(self, obj=None, f=None, dp=None):
        d = DEFAULT_DIGITS = 2
        if dp:
            decimal_precision_obj = self.pool['decimal.precision']
            ids = decimal_precision_obj.search(request.cr, request.uid, [('name', '=', dp)])
            if ids:
                d = decimal_precision_obj.browse(request.cr, request.uid, ids)[0].digits
        elif obj and f:
            res_digits = getattr(obj._columns[f], 'digits', lambda x: ((16, DEFAULT_DIGITS)))
            if isinstance(res_digits, tuple):
                d = res_digits[1]
            else:
                d = res_digits(request.cr)[1]
        elif (hasattr(obj, '_field') and
                isinstance(obj._field, (float_field, function_field)) and
                obj._field.digits):
                d = obj._field.digits[1] or DEFAULT_DIGITS
        return d

    def _get_lang_dict(self):
        pool_lang = self.pool['res.lang']
        lang = self.localcontext.get('lang', 'en_US') or 'en_US'
        lang_ids = pool_lang.search(request.cr, request.uid, [('code', '=', lang)])[0]
        lang_obj = pool_lang.browse(request.cr, request.uid, lang_ids)
        lang_dict = {
            'lang_obj': lang_obj,
            'date_format': lang_obj.date_format,
            'time_format': lang_obj.time_format
        }
        self.lang_dict.update(lang_dict)
        self.default_lang[lang] = self.lang_dict.copy()
        return True

    def formatLang(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        """
            Assuming 'Account' decimal.precision=3:
                formatLang(value) -> digits=2 (default)
                formatLang(value, digits=4) -> digits=4
                formatLang(value, dp='Account') -> digits=3
                formatLang(value, digits=5, dp='Account') -> digits=5
        """
        if digits is None:
            if dp:
                digits = self.get_digits(dp=dp)
            else:
                digits = self.get_digits(value)

        if isinstance(value, (str, unicode)) and not value:
            return ''

        if not self.lang_dict_called:
            self._get_lang_dict()
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
                date = datetime_field.context_timestamp(request.cr, request.uid,
                                                        timestamp=date,
                                                        context=self.localcontext)
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
        self._get_lang_dict()

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

        current_user = self.pool['res.users'].browse(cr, uid, uid, context=context)

        # Website independance code
        website = False
        res_company = current_user.company_id

        try:
            website = request.website
            res_company = request.website.company_id
        except:
            pass

        values.update({
            'time': time,
            'user': current_user,
            'user_id': current_user.id,
            'formatLang': self.formatLang,
            'get_digits': self.get_digits,
            'render_doc': render_doc,
            'website': website,
            'res_company': res_company,
        })

        return view_obj.render(cr, uid, template, values, context=context)

    def get_pdf(self, report, record_id, context=None):
        """Used to return the content of a generated PDF.

        :returns: pdf
        """
        url = '/report/pdf/report/' + report.report_file + '/' + str(record_id)
        reqheaders = Headers(request.httprequest.headers)
        reqheaders.pop('Accept')
        reqheaders.add('Accept', 'application/pdf')
        reqheaders.pop('Content-Type')
        reqheaders.add('Content-Type', 'text/plain')
        response = Client(request.httprequest.app, BaseResponse).get(url, headers=reqheaders,
                                                                     follow_redirects=True)
        return response.data

    def get_action(self, cr, uid, ids, report_name, datas=None, context=None):
        """Used to return an action of type ir.actions.report.xml.

        :param report_name: Name of the template to generate an action for
        """
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

    def eval_params(self, dict_param):
        """Parse a dictionary generated by the webclient (javascript) into a dictionary
        understandable by a wizard controller (python).
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
