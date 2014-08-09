# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2014 Marcos Organizador de Negocios- Eneldo Serrata - http://marcos.do
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company like Marcos Organizador de Negocios.
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

from openerp.osv import osv, fields
from ..tools import to_word as amount_to_text
from openerp.osv.orm import except_orm
from openerp.tools.translate import _

from datetime import datetime


class account_voucher(osv.Model):
    _inherit = 'account.voucher'
    _columns = {
        "authorized": fields.boolean("Authorized?", help="Voucher must be authorized before been validated."),
    }

    def _get_journal(self, cr, uid, context=None):
        if context.get('type', False) == "receipt":
            try:
                default_receipt_journal_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).pos_config.shop_id.default_receipt_journal_id.id
            except Exception, e:
                raise except_orm(_('Configuracion pendiente!'), _('Su usuario no tiene una caja configurada para poder crear recibos.'))
            if not default_receipt_journal_id:
                raise except_orm(_('Configuracion pendiente!'), _('Debe configurar el diario de recibos para cada una de las tiendas.'))
            return self.pool.get("account.journal").search(cr, uid, [('id', '=', default_receipt_journal_id)], limit=1)
        else:
            return super(account_voucher, self)._get_journal(cr, uid, context=context)

    _defaults = {'journal_id': _get_journal}

    def onchange_amount(self, cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date,
                        payment_rate_currency_id, company_id, context=None):
        """ Inherited - add amount_in_word and allow_check_writting in returned value dictionary """
        if not context:
            context = {}
        default = super(account_voucher, self).onchange_amount(cr, uid, ids, amount, rate, partner_id, journal_id,
                                                               currency_id, ttype, date, payment_rate_currency_id,
                                                               company_id, context=context)
        if 'value' in default:
            amount = 'amount' in default['value'] and default['value']['amount'] or amount

            # Currency complete name is not available in res.currency model
            # Exceptions done here (EUR, USD, BRL) cover 75% of cases
            # For other currencies, display the currency code
            currency = self.pool['res.currency'].browse(cr, uid, currency_id, context=context)
            if currency.name.upper() == 'EUR':
                currency_name = 'Euro'
            elif currency.name.upper() == 'USD':
                currency_name = 'Dollars'
            elif currency.name.upper() == 'BRL':
                currency_name = 'reais'
            else:
                currency_name = currency.name
            # TODO : generic amount_to_text is not ready yet, otherwise language (and country) and currency can be passed
            # amount_in_word = amount_to_text(amount, context=context)
            amount_in_word = amount_to_text(amount, "pesos")
            default['value'].update({'amount_in_word': amount_in_word})
            if journal_id:
                allow_check_writing = self.pool.get('account.journal').browse(cr, uid, journal_id,
                                                                              context=context).allow_check_writing
                default['value'].update({'allow_check': allow_check_writing})
        return default

    def create(self, cr, uid, vals, context=None):

        # [Tipo de de account_voucher para proveedores]
        # pago por del wizar desde la factura de venta context  {u'lang': u'es_DO', u'default_amount': 3690, u'close_after_process': True, u'tz': u'America/Santo_Domingo', u'uid': 1, u'payment_expected_currency': 74, u'active_model': u'account.invoice', u'invoice_id': 12296, u'journal_type': u'sale', u'default_type': u'receipt', u'invoice_type': u'out_invoice', u'search_disable_custom_filters': True, u'default_reference': u'', u'default_partner_id': 23198, u'active_ids': [12296], u'type': u'receipt', u'active_id': 12296}
        # recibo de venta context {u'lang': u'es_DO', u'type': u'sale', u'tz': u'America/Santo_Domingo', u'uid': 1, u'default_type': u'sale'}
        # pago clinte context {u'lang': u'es_DO', u'type': u'receipt', u'tz': u'America/Santo_Domingo', u'uid': 1}

        # [Tipo de de account_voucher para proveedores]
        # Recibo de compra context {u'lang': u'es_DO', u'type': u'purchase', u'tz': u'America/Santo_Domingo', u'uid': 1, u'default_type': u'purchase'}
        # Pagos a proveedores context {u'lang': u'es_DO', u'type': u'payment', u'tz': u'America/Santo_Domingo', u'uid': 1}
        # escribir cheque context {u'lang': u'es_DO', u'type': u'payment', u'write_check': True, u'tz': u'America/Santo_Domingo', u'uid': 1}
        # pago por del wizar desde la factura de compra context {u'lang': u'es_DO', u'default_amount': 3189.75, u'close_after_process': True, u'tz': u'America/Santo_Domingo', u'uid': 1, u'payment_expected_currency': 74, u'active_model': u'account.invoice', u'invoice_id': 12877, u'journal_type': u'purchase', u'default_type': u'payment', u'invoice_type': u'in_invoice', u'search_disable_custom_filters': True, u'default_reference': False, u'default_partner_id': 30027, u'active_ids': [12877], u'type': u'payment', u'active_id': 12877}

        context = context or {}

        if context.get("type", False) in [u"receipt", u"sale"]:
            context.update({'rec_pos_seq': self.pool.get('ir.sequence').get(cr, uid, 'voucher.pos')})
            vals.update({"number": context.get("rec_pos_seq")})
            result = super(account_voucher, self).create(cr, uid, vals, context=context)
            if result and vals["amount"] > 0 and vals["type"] == "receipt":
                user_obj = self.pool.get("res.users")
                session_obj = self.pool.get("pos.session")
                pos_config_obj = self.pool.get("pos.config")
                session_id = session_obj.search(cr, uid, [('state', '=', 'opened'), ('user_id', '=', uid)], context=context)
                if session_id:
                    pos_config_id = [session_obj.read(cr, uid, session_id, ['config_id'])[0]["config_id"][0]]
                    pos_config = pos_config_obj.browse(cr, uid, pos_config_id)
                    default_journal_id = pos_config[0].shop_id.default_receipt_journal_id.id
                    if not default_journal_id:
                        raise except_orm(_('Configuracion pendiente!'), _('Debe configurar el diario de recibos para cada las tiendas.'))
                    pos_config_id = [pos_config[0].payment_pos.id] or pos_config_id
                    session_id = session_obj.search(cr, uid, [('state', '=', 'opened'), ('config_id', 'in', pos_config_id)], context=context)
                else:
                    user_obj  = user_obj.browse(cr, uid, uid, context=context)
                    pos_config_id = user_obj.pos_config.payment_pos.id or user_obj.pos_config.id
                    default_journal_id = user_obj.pos_config.shop_id.default_receipt_journal_id.id
                    if not default_journal_id:
                        raise except_orm(_('Configuracion pendiente!'), _('Debe configurar el diario de recibos para cada las tiendas.'))
                    session_id = session_obj.search(cr, uid, [('state', '=', 'opened'), ('config_id', '=', pos_config_id)], context=context)
                if not session_id:
                    raise except_orm(_('Caja Cerrada!'), _('La cajera no ha iniciado su terminal.'))
                values ={
                    'name': context.get("rec_pos_seq"),
                    'partner_id': vals["partner_id"],
                    'date_order': datetime.strftime(datetime.today(), "%Y-%m-%d %H:%M:%S"),
                    'session_id': session_id[0],
                    'sale_journal': default_journal_id,
                    # TODO get correct pricelist_id
                    'pricelist_id': 1,
                    'parent_return_order': '',
                    'type': 'receipt',
                    'pos_reference': result,
                    'temp_name': self.pool.get("res.partner").read(cr, uid, vals["partner_id"], ["name"])["name"]
                    }
                context['empty_order'] = True
                context['pos_receipt'] = True
                order_id = self.pool.get('pos.order').create(cr, uid, values, context=context)
                    # TODO get product/service especially used for pos.order receipt.
                # Must not have taxes and the proper account for billing.
                product_obj = self.pool.get('product.product').\
                    browse(cr, uid, 1, context=context)
                values = {
                    'order_id': order_id,
                    'name': product_obj.name,
                    'product_id': product_obj.id,
                    'price_unit': vals["amount"]
                    }
                self.pool.get('pos.order.line').create(cr, uid, values, context=context)

            return result

        return super(account_voucher, self).create(cr, uid, vals, context=context)

    def action_authorize(self, cr, uid, ids, context=None):
        """
        This function will mark the voucher as authorized for validation.

        """

        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        voucher = self.pool.get('account.voucher').browse(cr, uid, ids, context)[0]
        voucher.write({'authorized': True}, context=context)
        return True

    def print_receipt(self, cr, uid, ids, context=None):
        """
        This function prints the customer receipt.

        """

        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        datas = {
                 'model': 'account.voucher',
                 'ids': ids,
                 'form': self.read(cr, uid, ids[0], context=context),
        }
        return {'type': 'ir.actions.report.xml', 'report_name': 'marcos.customer.receipt', 'datas': datas, 'nodestroy': True}

    def print_check_request(self, cr, uid, ids, context=None):
        """
        This function prints the check request.

        """

        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        datas = {
                 'model': 'account.voucher',
                 'ids': ids,
                 'form': self.read(cr, uid, ids[0], context=context),
        }
        return {'type': 'ir.actions.report.xml', 'report_name': 'marcos.check.request', 'datas': datas, 'nodestroy': True}

    def print_check_bpd(self, cr, uid, ids, context=None):
        """
        This function prints the check for Banco Popular Dominicano.

        """

        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        datas = {
                 'model': 'account.voucher',
                 'ids': ids,
                 'form': self.read(cr, uid, ids[0], context=context),
        }
        return {'type': 'ir.actions.report.xml', 'report_name': 'cheque.popular', 'datas': datas, 'nodestroy': True}

    def remove_auto_paymment(self, cr, uid, ids, context=None):
            voucher_line_obj = self.pool.get("account.voucher.line")
            lines_dr = [line.id for line in self.browse(cr, uid, ids[0]).line_dr_ids]
            lines_cr = [line.id for line in self.browse(cr, uid, ids[0]).line_cr_ids]
            voucher_line_obj.write(cr, uid, lines_dr+lines_cr, {"amount": 0.00, "reconcile": False}, context=context)
            return True

    def action_move_line_create(self, cr, uid, ids, context=None):
        voucher_line_obj = self.pool.get("account.voucher.line")
        line_to_remove_ids = []
        for line in self.browse(cr, uid, ids[0]).line_dr_ids+self.browse(cr, uid, ids[0]).line_cr_ids:
            if line.amount == 0:
                line_to_remove_ids.append(line.id)
        voucher_line_obj.unlink(cr, uid, line_to_remove_ids)
        return super(account_voucher, self).action_move_line_create(cr, uid, ids, context=context)