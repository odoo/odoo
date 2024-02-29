# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

import time


class PosOnlineDeliveryProvider(models.Model):
    _name = 'pos.online.delivery.provider'
    _description = 'Online Delivery Provider'
    _order = 'module_state, state desc, sequence, name'
    _check_company_auto = True

    # Configuration fields
    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", help="Define the display order")
    state = fields.Selection(
        string="State",
        help="In test mode, request are sent to the sandbox api.",
        selection=[('disabled', "Disabled"), ('enabled', "Enabled"), ('test', "Test Mode")],
        default='disabled', required=True, copy=False)
    code = fields.Selection(
        string="Code",
        help="The technical code of this online delivery provider.",
        selection=[('none', "No Provider Set")],
        default='none',
        required=True,
    )
    company_id = fields.Many2one(  # Indexed to speed-up ORM searches (from ir_rule or others)
        string="Company", comodel_name='res.company', default=lambda self: self.env.company.id,
        required=True, index=True)
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', copy=False, help="The payment method and its journal should be created especially for this delivery service.")
    image_128 = fields.Image("Delivery Provider Logo", max_width=128, max_height=128)
    client_id = fields.Char("Client ID", help='', copy=False)
    client_secret = fields.Char("Client Secret", copy=False)
    access_token = fields.Char(copy=False)
    access_token_expiration_timestamp = fields.Float(copy=False)
    config_ids = fields.Many2many('pos.config', 'pos_config_delivery_provider_rel', 'delivery_provider_id', 'config_id', string='Point of Sale')
    available_pos_category_ids = fields.Many2many('pos.category', string='Available Point of Sale Categories', compute='_compute_available_pos_category_ids')
    pos_category_ids = fields.Many2many('pos.category', string='Point of Sale Categories', help='The categories of products that will be sent for the menu.')
    last_menu_synchronization = fields.Datetime('Last Menu Synchronization', copy=False)

    # Module-related fields
    module_id = fields.Many2one(string="Corresponding Module", comodel_name='ir.module.module')
    module_state = fields.Selection(string="Installation State", related='module_id.state', store=True)  # Stored for sorting.

    @api.depends('config_ids')
    def _compute_available_pos_category_ids(self):
        configs_to_check = self.config_ids or self.env['pos.config'].search([('company_id', '=', self.company_id.id)])
        categogy_domain = self.env['pos.category'].search([])
        for config_id in configs_to_check:
            if config_id.limit_categories:
                categogy_domain = categogy_domain & config_id.iface_available_categ_ids
        self.available_pos_category_ids = categogy_domain

    @api.onchange('state')
    def _onchange_state(self):
        self.ensure_one()
        if self.state in ('enabled', 'test'):
            if not self.payment_method_id:
                raise ValidationError(_('Please select a payment method for this delivery provider. We suggest you to create a specific journal and payment method specific to this provider.'))
            if not self.client_id or not self.client_secret:
                raise ValidationError(_('Please fill in the client id and client secret for this delivery provider.'))

    def _new_order(self, order_id):
        # notify the pos sessions / preparation screens
        pass

    def _get_access_token(self) -> str:
        self.ensure_one()
        return (self.access_token_expiration_timestamp or 0) > time.time() \
            and self.access_token or self._refresh_access_token()

    def _refresh_access_token(self) -> str:
        pass

    def _upload_menu(self):
        pass

    def _accept_order(self, id: int, status: str = ""):
        pass

    def _reject_order(self, id: int, rejected_reason: str = "busy"):
        pass

    def _get_delivery_acceptation_time(self):
        pass

    def button_immediate_install(self):
        """ Install the module and reload the page.

        Note: `self.ensure_one()`

        :return: The action to reload the page.
        :rtype: dict
        """
        if self.module_id and self.module_state != 'installed':
            self.module_id.button_immediate_install()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def ensure_enabled(self):
        pass
