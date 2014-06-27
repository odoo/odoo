# -*- coding: utf-'8' "-*-"
import urlparse

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_ccavenue.controllers.main import CCAvenueController
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare


class AcquirerCCAvenue(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_ccavenue_urls(self, cr, uid, environment, context=None):
        """ CCAvenue URLs
        """
        return {
            'ccavenue_form_url': 'https://www.ccavenue.com/shopzone/cc_details.jsp',
        }

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerCCAvenue, self)._get_providers(cr, uid, context=context)
        providers.append(['ccavenue', 'CCAvenue'])
        return providers

    _columns = {
        'merchant_id': fields.char('Merchant_id', required_if_provider='ccavenue'),
        'working_key': fields.char('Working Key', required_if_provider='ccavenue'),
    }


    def ccavenue_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        ccavenue_tx_values = dict(tx_values)
        ccavenue_tx_values.update({
            'Merchant_Id': acquirer.merchant_id,
            'Amount': tx_values['amount'],
            'Order_Id': tx_values['reference'],
            'Currency': tx_values['currency'],
            'Redirect_Url': '%s' % urlparse.urljoin(base_url, CCAvenueController._return_url),
            'WorkingKey': acquirer.working_key,
            'TxnType': 'A',
            'actionID': 'TXN',
            'billing_cust_name': partner_values['first_name'],
            'billing_cust_address': partner_values['address'],
            'billing_cust_email': partner_values['email'],
        })
        return partner_values, ccavenue_tx_values

    def ccavenue_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_ccavenue_urls(cr, uid, acquirer.environment, context=context)['ccavenue_form_url']

