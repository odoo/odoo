from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nFrPdpPartnerLookup(models.TransientModel):
    _name = 'l10n_fr_pdp.partner.lookup'
    _description = 'Partner Lookup'

    partner_id = fields.Many2one('res.partner', required=True)
    available_annuaire_line_ids = fields.One2many(
        comodel_name='l10n_fr_pdp.annuaire.line',
        inverse_name='lookup_id',
        string="Available Annuaire Lines",
    )
    line_count = fields.Integer(compute='_compute_line_count')
    selected_line_id = fields.Many2one(
        comodel_name='l10n_fr_pdp.annuaire.line',
        string="Selected Line",
        # A domain on a many2many id list is evaluated client-side as commands,
        # so the dropdown stays empty. Match the saved parent instead.
        domain="[('lookup_id', '=', id)]",
        compute='_compute_selected_line_id',
        readonly=False,
        store=True,
    )

    @api.depends('available_annuaire_line_ids')
    def _compute_line_count(self):
        for wizard in self:
            wizard.line_count = len(wizard.available_annuaire_line_ids)

    @api.depends('available_annuaire_line_ids')
    def _compute_selected_line_id(self):
        for wizard in self:
            wizard.selected_line_id = wizard.available_annuaire_line_ids[:1]

    def action_change_pdp_endpoint(self):
        self.ensure_one()
        if self.selected_line_id.lookup_id != self or not self.selected_line_id.identifier:
            raise UserError(_("Select a billing address."))
        identifier = self.selected_line_id.identifier
        partner = self.partner_id
        # Changing the EAS recomputes the endpoint from the bare SIREN.
        # Apply the chosen annuaire identifier after that recompute.
        partner.write({
            'peppol_eas': '0225',
            'ubl_cii_format': 'ubl_21_fr',
        })
        partner.peppol_endpoint = identifier
        return {'type': 'ir.actions.act_window_close'}


class L10nFrPdpAnnuaireLine(models.TransientModel):
    _name = 'l10n_fr_pdp.annuaire.line'
    _description = 'Annuaire Line'
    _rec_name = 'identifier'

    lookup_id = fields.Many2one('l10n_fr_pdp.partner.lookup', required=True, ondelete='cascade')
    identifier = fields.Char()
    platform_id = fields.Char()
    nature = fields.Char()
