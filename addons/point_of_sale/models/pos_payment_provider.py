from odoo import api, fields, models


class PosPaymentProvider(models.Model):
    _name = 'pos.payment.provider'
    _description = 'Point of Sale Payment Provider (terminal)'
    _order = 'module_state, mode desc, name'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Selection([
        ('none', 'No Provider Set')], string='Code',
        help='The technical code of this payment provider(terminal).',
        default='none', required=True,
    )
    mode = fields.Selection([
        ('disabled', 'Disabled'), ('enabled', 'Enabled'), ('test', 'Test Mode')], string='Mode',
        help='In test mode, a fake payment is processed through a test payment interface.\n'
             'This mode is advised when setting up the provider.',
        default='disabled', required=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id, required=True, index=True)
    pos_payment_method_ids = fields.One2many(comodel_name='pos.payment.method', inverse_name='pos_payment_provider_id', string='Supported Terminal', copy=False)

    # Kanban view fields
    image_128 = fields.Image(string='Image', max_width=128, max_height=128)

    # Module-related fields
    module_id = fields.Many2one(comodel_name='ir.module.module', string='Corresponding Module')
    module_state = fields.Selection(related='module_id.state', string='Installation State')

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'code', 'mode', 'company_id', 'pos_payment_method_ids']

    def _load_pos_data(self, data):
        fields = self._load_pos_data_fields(self.id)
        data = self.search_read([], fields, load=False)
        return {
            'data': data,
            'fields': fields,
        }

    def button_immediate_install(self):
        """ Install the module and reload the page.

        Note: `self.ensure_one()`

        :return: The action to reload the page.
        :rtype: dict
        """
        self.ensure_one()
        if self.module_id and self.module_state != 'installed':
            self.module_id.button_immediate_install()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
