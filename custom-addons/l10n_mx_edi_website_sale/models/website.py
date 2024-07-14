# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _lt


class Website(models.Model):
    _inherit = 'website'

    def _get_checkout_steps(self, current_step=None):
        """ Override of `website_sale` to add an "Invoicing info" step when needed.

        If `current_step` is provided, returns only the corresponding step.

        Note: self.ensure_one()

        :param str current_step: The xmlid of the current step, defaults to None.
        :rtype: list
        :return: A list with the following structure:
            [
                [xmlid],
                {
                    'name': str,
                    'current_href': str,
                    'main_button': str,
                    'main_button_href': str,
                    'back_button': str,
                    'back_button_href': str
                }
            ]
        """
        checkout_steps = super()._get_checkout_steps(current_step=None)
        order = self.sale_get_order()
        l10n_cl_is_extra_info_needed = order.company_id.country_code == 'MX'
        if l10n_cl_is_extra_info_needed:
            previous_step = next(
                step for step in checkout_steps if 'website_sale.checkout' in step[0]
            )
            previous_step_index = checkout_steps.index(previous_step)
            next_step_index = previous_step_index+2
            checkout_steps.insert(previous_step_index+1, (
                ['l10n_mx_edi_website_sale.l10n_mx_edi_invoicing_info'], {
                'name': _lt("Invoicing info"),
                'current_href': '/shop/l10n_mx_invoicing_info',
                'main_button': _lt("Continue checkout"),
                'main_button_href': previous_step[1]['main_button_href'],
                'back_button':  _lt("Return to shipping"),
                'back_button_href': '/shop/checkout',
            }))
            checkout_steps[previous_step_index][1]['main_button_href'] = '/shop/l10n_mx_invoicing_info'
            if order.partner_id and order.partner_id.country_id.code != 'MX':
                checkout_steps[next_step_index][1]['back_button'] = _lt("Return to invoicing info")
                checkout_steps[next_step_index][1]['back_button_href'] = '/shop/l10n_mx_invoicing_info'

        if current_step:
            return next(
                step for step in checkout_steps if current_step in step[0]
            )[1]
        else:
            return checkout_steps
