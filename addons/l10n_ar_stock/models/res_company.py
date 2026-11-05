from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ar_arba_cit = fields.Char(
        string="CIT",
        groups='base.group_system',
        help="Argentina: Tax identification code (Clave de Identificación Tributaria) issued by ARBA, used with the CUIT to log in to the COT service.",
    )
    l10n_ar_arba_cot_environment = fields.Selection(
        selection=[
            ('demo', "Demo"),
            ('testing', "Testing"),
            ('production', "Production"),
        ],
        string="ARBA COT Environment",
        help="Argentina: ARBA service generating the COT (Código de Operación de Traslado), the electronic delivery guide required to transport goods. Leave empty to disable the COT.",
    )
    l10n_ar_arba_cot_file_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="COT File Sequence",
        copy=False,
        help="Argentina: Sequence numbering the COT files sent to ARBA.",
    )

    def _l10n_ar_get_arba_cot_company(self):
        """ Return the closest company in the hierarchy, starting from itself, with a CUIT, whose CUIT and CIT are used for the COT. """
        self.ensure_one()
        return self.parent_ids[::-1].filtered('vat')[:1] or self

    def _l10n_ar_get_arba_cot_file_sequence_num(self):
        self.ensure_one()
        if not self.l10n_ar_arba_cot_file_sequence_id:
            self.l10n_ar_arba_cot_file_sequence_id = self.env['ir.sequence'].sudo().create({
                'name': self.env._("%s COT File Sequence", self.name),
                'company_id': self.id,
                'padding': 6,
            })
        return self.l10n_ar_arba_cot_file_sequence_id.next_by_id()
