# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_it_edi_doi_ids = fields.One2many(
        'l10n_it_edi_doi.declaration_of_intent',
        'partner_id',
        string="Available Declarations of Intent of this partner",
        domain=lambda self: [('company_id', '=', self.env.company.id)],
    )

    def l10n_it_edi_doi_action_open_declarations(self):
        self.ensure_one()
        return {
            'name': _("Declaration of Intent of %s", self.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_it_edi_doi.declaration_of_intent',
            'domain': [('partner_id', '=', self.commercial_partner_id.id)],
            'views': [(self.env.ref('l10n_it_edi_doi.view_l10n_it_edi_doi_tree').id, 'list'),
                      (self.env.ref('l10n_it_edi_doi.view_l10n_it_edi_doi_form').id, 'form')],
            'context': {
                'default_partner_id': self.id,
            },
        }
