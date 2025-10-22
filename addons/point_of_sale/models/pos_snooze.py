from odoo import api, fields, models
from odoo.fields import Datetime


class PosSnooze(models.Model):
    """ Used to register the snoozing of a product in a pos.session.

    If a there is a pos.product.template.snooze model with a product_template_id and a pos_config_id
    and the current time is between start_time and end_time then that product
    is currently disabled for the pos_config.
    """

    _name = 'pos.product.template.snooze'
    _description = "Point of Sale Product Snooze"
    _order = "id desc"
    _inherit = ['pos.load.mixin']

    product_template_id = fields.Many2one('product.template', string='Product', ondelete="cascade", required=True)
    pos_config_id = fields.Many2one('pos.config', string='POS Config', ondelete="cascade", required=True, index=True)
    start_time = fields.Datetime(string='Start Time', required=True)
    end_time = fields.Datetime(string='End Time', required=False)

    @api.model
    def get_active_snoozes(self, config_id, product_id):
        """
        Find active snoozes for a specific pos session and product template combination
        Active means that the start time is before the current time and end time is after
        the current time.
        """
        now = Datetime.now()

        domain = [
                ('start_time', '<=', now),
                ('end_time', '>=', now),
                ('pos_config_id', '=', config_id),
                ('product_template_id', '=', product_id),
        ]

        return self.search_read(domain)
