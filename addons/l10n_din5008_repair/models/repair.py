from odoo import models, fields
from odoo.addons import repair


class RepairOrder(repair.RepairOrder):

    l10n_din5008_printing_date = fields.Date(default=fields.Date.today, store=False)
