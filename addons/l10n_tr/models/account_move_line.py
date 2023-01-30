from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_tr_exception_code_id = fields.Many2one(comodel_name='l10n_tr.exception_reason')
    l10n_tr_available_exception_code_ids = fields.Many2many(
        comodel_name='l10n_tr.exception_reason', store=False,
        compute='_compute_l10n_tr_available_exception_code_ids')

    @api.depends('tax_ids')
    def _compute_l10n_tr_available_exception_code_ids(self):
        for line in self:
            line.l10n_tr_available_exception_code_ids = line.tax_ids.l10n_tr_exception_code_ids

    @api.constrains('tax_ids')
    def _check_l10n_tr_tax_compatibility(self):
        incompatible_tax_groups = (
            self.env.ref('l10n_tr.tax_group_vat_partial_withdrawal')
            + self.env.ref('l10n_tr.tax_group_not_subjected')
            + self.env.ref('l10n_tr.tax_group_zero_vat')
            + self.env.ref('l10n_tr.tax_group_vat_full')
        ).ids
        faulty_lines = self.filtered(
            lambda line: len(line.tax_ids.filtered_domain([('tax_group_id', 'in', incompatible_tax_groups)])) > 1
        )
        if faulty_lines:
            raise ValidationError(_(
                'You cannot have more than one tax from each tax group in a line. '
                'Please check the taxes on %s in %s',
                ','.join(faulty_lines.mapped('name')),
                ','.join(set(faulty_lines.move_id.mapped('name')))
            ))
