# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_ar_get_parent_vat(self):
        """ Return the CUIT the company withholds with: its own, or the one of its closest parent having one. """
        self.ensure_one()
        return next(filter(None, reversed(self.sudo().parent_ids.mapped('vat'))), False)

    def _l10n_ar_get_same_vat_companies(self):
        """ Return the companies of the hierarchy withholding with the same CUIT as this one,
            each CUIT being a withholding agent of its own. """
        self.ensure_one()
        vat = self._l10n_ar_get_parent_vat()
        return self.env['res.company'].sudo().search([
            ('id', 'child_of', self.root_id.id),
        ]).filtered(lambda company: company._l10n_ar_get_parent_vat() == vat)
