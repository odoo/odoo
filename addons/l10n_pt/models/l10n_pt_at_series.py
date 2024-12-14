from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nPtATSeries(models.Model):
    _name = "l10n_pt.at.series"
    _description = "Mapping between Odoo Series and the Official Series for the Autoridade Tributária (AT)"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of
    _rec_name = 'prefix'

    type = fields.Selection(
        string="Type of the series",
        selection=[
            ('out_invoice_ft', 'Invoice (FT)'),
            ('out_receipt_fr', 'Invoice/Receipt (FR)'),
            ('out_invoice_fs', 'Simplified Invoice (FS)'),
            ('out_refund_nc', 'Credit Note (NC)'),
        ],
        required=True,
    )
    prefix = fields.Char("Prefix of the series", required=True)
    at_code = fields.Char("AT code for the series", required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    date_end = fields.Date("End Date")
    formation_series = fields.Boolean("Formation Series")
    active = fields.Boolean(compute='_compute_active', search='_search_active')

    _prefix_company_uniq = models.Constraint(
        'unique(company_id, prefix)',
        'The AT Series prefix must be unique.',
    )
    _at_code_uniq = models.Constraint(
        'unique(at_code)',
        'The AT code must be unique.',
    )

    def _compute_active(self):
        for at_series in self:
            at_series.active = at_series.date_end >= fields.Date.today() if at_series.date_end else True

    def _get_at_code(self):
        self.ensure_one()
        if not self.active:
            raise UserError(_("The series %(prefix)s is not active.", prefix=self.prefix))
        return self.at_code

    def _search_active(self, operator, value):
        if operator not in ['in', '=', '!=']:
            raise ValueError(_('This operator is not supported'))
        now = fields.Datetime.now()
        if (operator == '=' and value) or (operator == '!=' and not value):
            domain = ['|', ('date_end', '=', False), ('date_end', '>=', now)]
        else:
            domain = ['|', ('date_end', '=', False), ('date_end', '<', now)]
        return domain

    def write(self, vals):
        if vals.get('type') or vals.get("prefix") or vals.get("at_code") or vals.get("formation_series"):
            if self.env['account.move'].search_count([
                ('sequence_prefix', 'in', [f"{at_series.prefix}/" for at_series in self]),
                ('inalterable_hash', "!=", False),
            ], limit=1):
                raise UserError(_("You cannot change the type, prefix or AT code of a series that has already been used."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used(self):
        for at_series in self:
            if self.env['account.move'].search_count([
                ('sequence_prefix', '=', f"{at_series.prefix}/"),
                ('inalterable_hash', "!=", False),
            ], limit=1):
                raise UserError(_("You cannot delete a series that is used. It will automatically be archived after the End Date"))
