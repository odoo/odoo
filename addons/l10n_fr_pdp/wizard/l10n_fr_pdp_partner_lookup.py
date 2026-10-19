from odoo import api, fields, models


class L10nFrPdpPartnerLookup(models.TransientModel):
    _name = 'l10n_fr_pdp.partner.lookup'
    _description = 'Partner Lookup'

    available_annuaire_line_ids = fields.Many2many(
        comodel_name='l10n_fr_pdp.annuaire.line',
        string="Available Annuaire Lines",
    )

    selected_line_id = fields.Many2one(
        comodel_name='l10n_fr_pdp.annuaire.line',
        string="Selected Line",
        domain="[('id', 'in', available_annuaire_line_ids)]",
        compute='_compute_selected_line_id',
        readonly=False,
        store=True,
    )

    partner_id = fields.Many2one('res.partner', required=True)

    @api.depends('available_annuaire_line_ids')
    def _compute_selected_line_id(self):
        for record in self:
            record.selected_line_id = record.available_annuaire_line_ids[0]

    def action_change_pdp_endpoint(self):
        self.ensure_one()
        # Change the peppol endpoint of the partner by the selected annuaire line
        self.partner_id.routing_endpoint = self.selected_line_id.identifier


class L10nFrPdpAnnuaireLine(models.TransientModel):
    _name = 'l10n_fr_pdp.annuaire.line'
    _description = 'Annuaire Line'
    _rec_name = 'identifier'

    identifier = fields.Char()
    platform_id = fields.Char()
    nature = fields.Char()
