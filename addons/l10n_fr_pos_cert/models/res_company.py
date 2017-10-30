from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pos_cert_sequence_id = fields.Many2one('ir.sequence')

    # To do in master : refactor to set sequences more generic
    # Do basically the same as in l10n_fr_certification for automatically fill this field