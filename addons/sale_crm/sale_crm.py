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

from datetime import date
from openerp import tools
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, fields

MONTHS = {
    "monthly": 1,
    "semesterly": 3,
    "semiannually": 6,
    "annually": 12
}

class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'categ_ids': fields.many2many('crm.case.categ', 'sale_order_category_rel', 'order_id', 'category_id', 'Categories', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]")
    }


class crm_case_section(osv.osv):
    _inherit = 'crm.case.section'

    def _get_created_quotation_per_duration(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, [])
        obj = self.pool.get('sale.order')
        first_day = date.today().replace(day=1)

        for section in self.browse(cr, uid, ids, context=context):
            dates = [first_day + relativedelta(months=-(MONTHS[section.target_duration]*(key+1)-1)) for key in range(0, 5)]
            rate_invoice = []
            for when in range(0, 5):
                domain = [("section_id", "=", section.id), ('state', 'in', ['draft', 'sent']), ('date_order', '>=', dates[when].strftime(tools.DEFAULT_SERVER_DATE_FORMAT))]
                if when:
                    domain += [('date_order', '<', dates[when-1].strftime(tools.DEFAULT_SERVER_DATE_FORMAT))]
                rate = 0
                opportunity_ids = obj.search(cr, uid, domain, context=context)
                for invoice in obj.browse(cr, uid, opportunity_ids, context=context):
                    rate += invoice.amount_total
                rate_invoice.append(rate)
            rate_invoice.reverse()
            res[section.id] = rate_invoice
        return res

    def _get_validate_saleorder_per_duration(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, [])
        obj = self.pool.get('sale.order')
        first_day = date.today().replace(day=1)

        for section in self.browse(cr, uid, ids, context=context):
            dates = [first_day + relativedelta(months=-(MONTHS[section.target_duration]*(key+1)-1)) for key in range(0, 5)]
            rate_invoice = []
            for when in range(0, 5):
                domain = [("section_id", "=", section.id), ('state', 'not in', ['draft', 'sent']), ('date_confirm', '>=', dates[when].strftime(tools.DEFAULT_SERVER_DATE_FORMAT))]
                if when:
                    domain += [('date_confirm', '<', dates[when-1].strftime(tools.DEFAULT_SERVER_DATE_FORMAT))]
                rate = 0
                opportunity_ids = obj.search(cr, uid, domain, context=context)
                for invoice in obj.browse(cr, uid, opportunity_ids, context=context):
                    rate += invoice.amount_total
                rate_invoice.append(rate)
            rate_invoice.reverse()
            res[section.id] = rate_invoice
        return res

    def _get_sent_invoice_per_duration(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, [])
        obj = self.pool.get('account.invoice.report')
        first_day = date.today().replace(day=1)

        for section in self.browse(cr, uid, ids, context=context):
            dates = [first_day + relativedelta(months=-(MONTHS[section.target_duration]*(key+1)-1)) for key in range(0, 5)]
            rate_invoice = []
            for when in range(0, 5):
                domain = [("section_id", "=", section.id), ('state', 'not in', ['draft', 'cancel']), ('date', '>=', dates[when].strftime(tools.DEFAULT_SERVER_DATE_FORMAT))]
                if when:
                    domain += [('date', '<', dates[when-1].strftime(tools.DEFAULT_SERVER_DATE_FORMAT))]
                rate = 0
                opportunity_ids = obj.search(cr, uid, domain, context=context)
                for invoice in obj.browse(cr, uid, opportunity_ids, context=context):
                    rate += invoice.price_total
                rate_invoice.append(rate)
            rate_invoice.reverse()
            res[section.id] = rate_invoice
        return res

    _columns = {
        'quotation_ids': fields.one2many('sale.order', 'section_id',
            string='Quotations', readonly=True,
            domain=[('state', 'in', ['draft', 'sent', 'cancel'])]),
        'sale_order_ids': fields.one2many('sale.order', 'section_id',
            string='Sale Orders', readonly=True,
            domain=[('state', 'not in', ['draft', 'sent', 'cancel'])]),
        'invoice_ids': fields.one2many('account.invoice', 'section_id',
            string='Invoices', readonly=True,
            domain=[('state', 'not in', ['draft', 'cancel'])]),

        'forecast': fields.integer(string='Total forecast'),
        'target_invoice': fields.integer(string='Target Invoicing'),
        'created_quotation_per_duration': fields.function(_get_created_quotation_per_duration, string='Rate of created quotation per duration', type="string", readonly=True),
        'validate_saleorder_per_duration': fields.function(_get_validate_saleorder_per_duration, string='Rate of validate sales orders per duration', type="string", readonly=True),
        'sent_invoice_per_duration': fields.function(_get_sent_invoice_per_duration, string='Rate of sent invoices per duration', type="string", readonly=True),
    }

    def action_forecast(self, cr, uid, id, value, context=None):
        return self.write(cr, uid, [id], {'forecast': value}, context=context)

class res_users(osv.Model):
    _inherit = 'res.users'
    _columns = {
        'default_section_id': fields.many2one('crm.case.section', 'Default Sales Team'),
    }


class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }
    _defaults = {
        'section_id': lambda self, cr, uid, c=None: self.pool.get('res.users').browse(cr, uid, uid, c).default_section_id.id or False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
