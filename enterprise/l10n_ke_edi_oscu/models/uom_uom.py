# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Uom(models.Model):
    _inherit = 'uom.uom'

    l10n_ke_quantity_unit_id = fields.Many2one(
        'l10n_ke_edi_oscu.code',
        readonly=False,
        string="Quantity Unit",
        domain=[('code_type', '=', '10')],
        help="KRA code that describes the type of unit used.",
    )

    def _l10n_ke_get_validation_messages(self):
        """ Check that UoMs are configured correctly for sending product configuration to eTIMS """
        messages = {}

        misconfigured_uoms = self.filtered(lambda u: not u.l10n_ke_quantity_unit_id)
        if misconfigured_uoms:
            messages['uom_code_missing'] = {
                'message': _("Some units of measure are missing a corresponding KRA code where one must be configured."),
                'action_text': _("View UoM(s)"),
                'action': misconfigured_uoms._l10n_ke_action_open_uoms(),
                'blocking': True,
            }

        return messages

    def _l10n_ke_action_open_uoms(self, title=None):
        """ Open a view of the UoM fields that must be set to register products with eTIMS. """
        res = {
            'name': title or _("UoM(s)"),
            'type': 'ir.actions.act_window',
            'res_model': 'uom.uom',
            'domain': [('id', 'in', self.ids)],
            'view_mode': 'list',
            'views': [(self.env.ref('l10n_ke_edi_oscu.product_uom_l10n_ke_tree').id, 'list'), (False, 'form')],
            'context': {'create': False, 'delete': False},
        }
        return res


class UoMCategory(models.Model):
    _inherit = "uom.category"

    fiscal_country_codes = fields.Char(compute="_compute_fiscal_country_codes")

    @api.depends_context("allowed_company_ids")
    def _compute_fiscal_country_codes(self):
        for record in self:
            record.fiscal_country_codes = ",".join(self.env.companies.mapped("account_fiscal_country_id.code"))
