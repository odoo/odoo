# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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
from urllib import quote as quote

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import float_repr

_logger = logging.getLogger(__name__)
try:
    from mako.template import Template as MakoTemplate
except ImportError:
    _logger.warning("payment_acquirer: mako templates not available, payment acquirer will not work!")


class acquirer(osv.Model):
    _name = 'portal.payment.acquirer'
    _description = 'Online Payment Acquirer'
    
    _columns = {
        'name': fields.char('Name', required=True),
        'form_template': fields.text('Payment form template (HTML)', translate=True, required=True), 
        'visible': fields.boolean('Visible', help="Make this payment acquirer available in portal forms (Customer invoices, etc.)"),
    }

    _defaults = {
        'visible': True,
    }

    def render(self, cr, uid, id, object, reference, currency, amount, context=None, **kwargs):
        """ Renders the form template of the given acquirer as a mako template  """
        if not isinstance(id, (int,long)):
            id = id[0]
        this = self.browse(cr, uid, id)
        if context is None:
            context = {}
        try:
            i18n_kind = _(object._description) # may fail to translate, but at least we try
            result = MakoTemplate(this.form_template).render_unicode(object=object,
                                                           reference=reference,
                                                           currency=currency,
                                                           amount=amount,
                                                           kind=i18n_kind,
                                                           quote=quote,
                                                           # context kw would clash with mako internals
                                                           ctx=context,
                                                           format_exceptions=True)
            return result.strip()
        except Exception:
            _logger.exception("failed to render mako template value for payment.acquirer %s: %r", this.name, this.form_template)
            return

    def _wrap_payment_block(self, cr, uid, html_block, amount, currency, context=None):
        if not html_block:
            link = '#action=account.action_account_config'
            payment_header = _('You can finish the configuration in the <a href="%s">Bank&Cash settings</a>') % link
            amount = _('No online payment acquirers configured')
            group_ids = self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id
            if any(group.is_portal for group in group_ids):
                return ''
        else:
            payment_header = _('Pay safely online')
            amount_str = float_repr(amount, self.pool.get('decimal.precision').precision_get(cr, uid, 'Account'))
            currency_str = currency.symbol or currency.name
            amount = u"%s %s" % ((currency_str, amount_str) if currency.position == 'before' else (amount_str, currency_str))
        result =  """<div class="payment_acquirers">
                         <div class="payment_header">
                             <div class="payment_amount">%s</div>
                             %s
                         </div>
                         %%s
                     </div>""" % (amount, payment_header)
        return result % html_block

    def render_payment_block(self, cr, uid, object, reference, currency, amount, context=None, **kwargs):
        """ Renders all visible payment acquirer forms for the given rendering context, and
            return them wrapped in an appropriate HTML block, ready for direct inclusion
            in an OpenERP v7 form view """
        acquirer_ids = self.search(cr, uid, [('visible', '=', True)])
        if not acquirer_ids:
            return
        html_forms = []
        for this in self.browse(cr, uid, acquirer_ids):
            content = this.render(object, reference, currency, amount, context=context, **kwargs)
            if content:
                html_forms.append(content)
        html_block = '\n'.join(filter(None,html_forms))
        return self._wrap_payment_block(cr, uid, html_block, amount, currency, context=context)  
