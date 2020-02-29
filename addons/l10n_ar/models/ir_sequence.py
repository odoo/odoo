# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class IrSequence(models.Model):

    _inherit = 'ir.sequence'

    l10n_ar_letter = fields.Selection(selection='_get_l10n_ar_letters', string='Letter')

    def _get_l10n_ar_letters(self):
        """ Return the list of values of the selection field. """
        return self.env['l10n_latam.document.type']._get_l10n_ar_letters()
