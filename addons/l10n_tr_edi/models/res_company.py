from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_tr_edi_provider = fields.Selection(
        selection=[],
        string="e-Document Provider",
        help="The integrator through which the e-Invoices, e-Archives and e-Dispatches are exchanged with the GİB. "
             "Without one, nothing is sent to the GİB.",
    )
