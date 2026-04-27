# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountImportSummary(models.TransientModel):
    _name = "account.import.summary"
    _description = "Account import summary view"
    _rec_name = 'import_summary_name'

    import_summary_account_ids = fields.Many2many('account.account')
    import_summary_journal_ids = fields.Many2many('account.journal')
    import_summary_move_ids = fields.Many2many('account.move')
    import_summary_partner_ids = fields.Many2many('res.partner')
    import_summary_tax_ids = fields.Many2many('account.tax')

    import_summary_name = fields.Char(default="Import Summary")
    import_summary_len_account = fields.Integer(compute='_compute_import_summary_len_account', export_string_translation=False)
    import_summary_len_journal = fields.Integer(compute='_compute_import_summary_len_journal', export_string_translation=False)
    import_summary_len_move = fields.Integer(compute='_compute_import_summary_len_move', export_string_translation=False)
    import_summary_len_partner = fields.Integer(compute='_compute_import_summary_len_partner', export_string_translation=False)
    import_summary_len_tax = fields.Integer(compute='_compute_import_summary_len_tax', export_string_translation=False)
    import_summary_have_data = fields.Boolean(compute='_compute_import_summary_have_data', export_string_translation=False)

    @api.depends('import_summary_account_ids')
    def _compute_import_summary_len_account(self):
        for record in self:
            record.import_summary_len_account = len(record.import_summary_account_ids)

    @api.depends('import_summary_journal_ids')
    def _compute_import_summary_len_journal(self):
        for record in self:
            record.import_summary_len_journal = len(record.import_summary_journal_ids)

    @api.depends('import_summary_move_ids')
    def _compute_import_summary_len_move(self):
        for record in self:
            record.import_summary_len_move = len(record.import_summary_move_ids)

    @api.depends('import_summary_partner_ids')
    def _compute_import_summary_len_partner(self):
        for record in self:
            record.import_summary_len_partner = len(record.import_summary_partner_ids)

    @api.depends('import_summary_tax_ids')
    def _compute_import_summary_len_tax(self):
        for record in self:
            record.import_summary_len_tax = len(record.import_summary_tax_ids)

    @api.depends(
        'import_summary_account_ids',
        'import_summary_journal_ids',
        'import_summary_move_ids',
        'import_summary_partner_ids',
        'import_summary_tax_ids'
    )
    def _compute_import_summary_have_data(self):
        for record in self:
            record.import_summary_have_data = bool(
                record.import_summary_account_ids or
                record.import_summary_journal_ids or
                record.import_summary_move_ids or
                record.import_summary_partner_ids or
                record.import_summary_tax_ids
            )

    def action_open_summary_view(self):
        self.ensure_one()
        return {
            "name": _("Import Summary"),
            "type": "ir.actions.act_window",
            "res_id": self.id,
            "view_mode": "form",
            "res_model": "account.import.summary",
        }

    def action_open_account_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account_base_import.action_open_coa_setup')
        action['domain'] = [('id', 'in', self.import_summary_account_ids.ids)]
        return action

    def action_open_journal_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_journal_form')
        action['domain'] = [('id', 'in', self.import_summary_journal_ids.ids)]
        return action

    def action_open_move_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_line_form')
        action['domain'] = [('id', 'in', self.import_summary_move_ids.ids)]
        return action

    def action_open_partner_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('base.action_partner_form')
        action['domain'] = [('id', 'in', self.import_summary_partner_ids.ids)]
        return action

    def action_open_tax_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_tax_form')
        action['domain'] = [('id', 'in', self.import_summary_tax_ids.ids)]
        return action
