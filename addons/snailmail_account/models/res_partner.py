from odoo import fields, models
from odoo.addons import account, snailmail


class ResPartner(account.ResPartner, snailmail.ResPartner):

    invoice_sending_method = fields.Selection(
        selection_add=[('snailmail', 'by Post')],
    )
