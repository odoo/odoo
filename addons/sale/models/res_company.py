# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import api, fields, models, _
from odoo.modules.module import get_module_resource
from odoo.modules.module import get_resource_path

class ResCompany(models.Model):
    _inherit = "res.company"

    portal_confirmation_sign = fields.Boolean(string='Online Signature', default=True)
    portal_confirmation_pay = fields.Boolean(string='Online Payment')
    quotation_validity_days = fields.Integer(default=30, string="Default Quotation Validity (Days)")

    # sale quotation onboarding
    sale_quotation_onboarding_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done"), ('closed', "Closed")], string="State of the sale onboarding panel", default='not_done')
    sale_onboarding_order_confirmation_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the onboarding confirmation order step", default='not_done')
    sale_onboarding_sample_quotation_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the onboarding sample quotation step", default='not_done')

    sale_onboarding_payment_method = fields.Selection([
        ('digital_signature', 'Sign online'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('other', 'Pay with another payment acquirer'),
        ('manual', 'Manual Payment'),
    ], string="Sale onboarding selected payment method")

    @api.model
    def action_close_sale_quotation_onboarding(self):
        """ Mark the onboarding panel as closed. """
        self.env.company.sale_quotation_onboarding_state = 'closed'

    @api.model
    def action_open_sale_onboarding_payment_acquirer(self):
        """ Called by onboarding panel above the quotation list."""
        self.env.company.get_chart_of_accounts_or_fail()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_open_sale_onboarding_payment_acquirer_wizard")
        return action

    def _get_sample_sales_order(self):
        """ Get a sample quotation or create one if it does not exist. """
        # use current user as partner
        partner = self.env.user.partner_id
        company_id = self.env.company.id
        # is there already one?
        sample_sales_order = self.env['sale.order'].search(
            [('company_id', '=', company_id), ('partner_id', '=', partner.id),
             ('state', '=', 'draft')], limit=1)
        if len(sample_sales_order) == 0:
            sample_sales_order = self.env['sale.order'].create({
                'partner_id': partner.id
            })
            # take any existing product or create one
            product = self.env['product.product'].search([], limit=1)
            if len(product) == 0:
                default_image_path = get_module_resource('product', 'static/img', 'product_product_13-image.png')
                product = self.env['product.product'].create({
                    'name': _('Sample Product'),
                    'active': False,
                    'image_1920': base64.b64encode(open(default_image_path, 'rb').read())
                })
                product.product_tmpl_id.write({'active': False})
            self.env['sale.order.line'].create({
                'name': _('Sample Order Line'),
                'product_id': product.id,
                'product_uom_qty': 10,
                'price_unit': 123,
                'order_id': sample_sales_order.id,
                'company_id': sample_sales_order.company_id.id,
            })
        return sample_sales_order

    @api.model
    def action_open_sale_onboarding_sample_quotation(self):
        """ Onboarding step for sending a sample quotation. Open a window to compose an email,
            with the edi_invoice_template message loaded by default. """
        sample_sales_order = self._get_sample_sales_order()
        template = self.env.ref('sale.email_template_edi_sale', False)

        message_composer = self.env['mail.compose.message'].with_context(
            default_use_template=bool(template),
            mark_so_as_sent=True,
            custom_layout='mail.mail_notification_paynow',
            proforma=self.env.context.get('proforma', False),
            force_email=True, mail_notify_author=True
        ).create({
            'res_id': sample_sales_order.id,
            'template_id': template and template.id or False,
            'model': 'sale.order',
            'composition_mode': 'comment'})

        # Simulate the onchange (like trigger in form the view)
        update_values = message_composer.onchange_template_id(template.id, 'comment', 'sale.order', sample_sales_order.id)['value']
        message_composer.write(update_values)

        message_composer.send_mail()

        self.set_onboarding_step_done('sale_onboarding_sample_quotation_state')

        self.action_close_sale_quotation_onboarding()

        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action.update({
            'views': [[self.env.ref('sale.view_order_form').id, 'form']],
            'view_mode': 'form',
            'target': 'main',
        })
        return action

    def get_and_update_sale_quotation_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time. """
        steps = [
            'base_onboarding_company_state',
            'account_onboarding_invoice_layout_state',
            'sale_onboarding_order_confirmation_state',
            'sale_onboarding_sample_quotation_state',
        ]
        return self.get_and_update_onbarding_state('sale_quotation_onboarding_state', steps)

    _sql_constraints = [('check_quotation_validity_days', 'CHECK(quotation_validity_days > 0)', 'Quotation Validity is required and must be greater than 0.')]
