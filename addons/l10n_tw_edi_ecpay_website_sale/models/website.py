# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)


class Website(models.Model):
    _inherit = 'website'

    def _get_checkout_step_list(self):
        checkout_steps = super()._get_checkout_step_list()
        order = self.sale_get_order()

        l10n_tw_is_extra_info_needed = order.company_id._is_ecpay_enabled() \
            and not order.partner_id.l10n_tw_edi_require_paper_format

        if l10n_tw_is_extra_info_needed:
            previous_step = next(
                step for step in checkout_steps if 'website_sale.checkout' in step[0]
            )
            previous_step_index = checkout_steps.index(previous_step)
            next_step_index = previous_step_index + 2
            checkout_steps.insert(previous_step_index + 1, (
                ['l10n_tw_edi_ecpay_website_sale.l10n_tw_edi_invoicing_info'], {
                    'name': _lt("Invoicing Info"),
                    'current_href': '/shop/l10n_tw_invoicing_info',
                    'main_button': _lt("Continue checkout"),
                    'main_button_href': previous_step[1]['main_button_href'],
                    'back_button': _lt("Return to shipping"),
                    'back_button_href': '/shop/checkout',
                }))
            checkout_steps[previous_step_index][1]['main_button_href'] = '/shop/l10n_tw_invoicing_info'
            if order.partner_id and order.partner_id.country_id.code != 'TW':
                checkout_steps[next_step_index][1]['back_button'] = _lt("Return to Invoicing Info")
                checkout_steps[next_step_index][1]['back_button_href'] = '/shop/l10n_tw_invoicing_info'
        return checkout_steps
