from odoo import api, fields, models


class L10n_Tr_EdiAliasWizard(models.TransientModel):
    _name = 'l10n_tr_edi.alias.wizard'
    _description = "Choose a GİB alias of a partner"

    partner_id = fields.Many2one(comodel_name='res.partner', required=True)
    alias_type = fields.Selection(
        selection=[('einvoice', "e-Invoice")],
        required=True,
    )
    alias_ids = fields.One2many(
        comodel_name='l10n_tr_edi.alias.wizard.line',
        inverse_name='wizard_id',
        string="Available Aliases",
        help="The aliases the e-Document provider lists for the partner, to pick from.",
    )
    selected_alias_id = fields.Many2one(
        comodel_name='l10n_tr_edi.alias.wizard.line',
        string="Alias",
        compute='_compute_selected_alias_id',
        store=True,
        readonly=False,
        domain="[('wizard_id', '=', id)]",
    )

    @api.model
    def _get_partner_alias_field(self, alias_type):
        """Return the name of the partner field holding the alias of `alias_type`."""
        return {'einvoice': 'l10n_tr_edi_einvoice_alias'}[alias_type]

    @api.depends('alias_ids', 'partner_id', 'alias_type')
    def _compute_selected_alias_id(self):
        for wizard in self:
            # The current alias while the GİB still lists it, else the first one listed.
            current_alias = wizard.partner_id[self._get_partner_alias_field(wizard.alias_type)]
            wizard.selected_alias_id = (
                wizard.alias_ids.filtered(lambda line: line.name == current_alias)[:1] or wizard.alias_ids[:1]
            )

    def action_validate(self):
        self.ensure_one()
        self.partner_id[self._get_partner_alias_field(self.alias_type)] = self.selected_alias_id.name


class L10n_Tr_EdiAliasWizardLine(models.TransientModel):
    _name = 'l10n_tr_edi.alias.wizard.line'
    _description = "GİB alias of a partner"

    wizard_id = fields.Many2one(comodel_name='l10n_tr_edi.alias.wizard', required=True, ondelete='cascade')
    name = fields.Char(required=True)
