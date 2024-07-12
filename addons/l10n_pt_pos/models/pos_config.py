from odoo import models, fields, _

from odoo.exceptions import UserError, RedirectWarning


class PosConfig(models.Model):
    _inherit = 'pos.config'

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_pt_pos_at_series_id = fields.Many2one("l10n_pt.at.series", string="Official Series of the Tax Authority")

    def _l10n_pt_pos_verify_config(self):
        if not self.l10n_pt_pos_at_series_id or self.l10n_pt_pos_at_series_id.type != "pos_order":
            raise RedirectWarning(
                _('You have to set an Official Series (of type POS order) for this POS configuration.'),
                {
                    "view_mode": "form",
                    "res_model": "pos.config",
                    "type": "ir.actions.act_window",
                    "res_id": self.id,
                    "views": [[self.env.ref("l10n_pt_pos.pos_pt_config_view_form").id, "form"]],
                },
                _("Go to the POS configuration")
            )
        if incorrect_products := self.env['product.product'].search([
            ('default_code', '=', False),
            ('available_in_pos', '=', True),
        ]).filtered(lambda p: len(p.taxes_id) != 1):
            raise RedirectWarning(
                _("All products should have one tax and an internal reference."),
                {
                    'type': 'ir.actions.act_window',
                    'name': 'Incorrect products',
                    'res_model': 'product.product',
                    'view_mode': 'tree',
                    'views': [[False, 'list'], [False, 'form']],
                    'domain': [('id', 'in', incorrect_products.ids)],
                },
                _("Incorrect products")
            )

    def open_ui(self):
        if not self.company_id.country_id or self.company_id.country_id.code != 'PT':
            return super().open_ui()
        self._l10n_pt_pos_verify_config()
        return super().open_ui()

    def write(self, vals):
        for config in self:
            if "l10n_pt_pos_at_series_id" not in vals:
                continue
            if (
                config.l10n_pt_pos_at_series_id
                and self.env['pos.order'].search_count([
                    ('config_id', '=', config.id),
                    ('l10n_pt_pos_inalterable_hash', '!=', False),
                ], limit=1)
            ):
                raise UserError(_("You cannot change the AT series of a POS configuration once it has been used."))
            if vals["l10n_pt_pos_at_series_id"] and config.search_count([
                ('l10n_pt_pos_at_series_id', '=', vals['l10n_pt_pos_at_series_id']),
                ('id', '!=', config.id),
            ], limit=1):
                raise UserError(_("You cannot use the same AT series for more than one POS configuration."))
        return super().write(vals)
