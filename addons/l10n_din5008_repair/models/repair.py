from odoo import models, fields


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    l10n_din5008_printing_date = fields.Date(default=fields.Date.today, store=False)
