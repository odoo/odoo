from odoo import api, models


class KpiProvider(models.AbstractModel):
    _inherit = 'kpi.provider'

    @api.model
    def get_account_kpi_summary(self):
        grouped_moves_to_report = self.env['account.move']._read_group([
            '|', ('state', '=', 'draft'),
            '&', ('state', '=', 'posted'), ('to_check', '=', True),
        ], ['journal_id'], ['journal_id'])

        FieldsSelection = self.env['ir.model.fields.selection'].with_context(lang=self.env.user.lang)
        journal_type_names = {x.value: x.name for x in FieldsSelection.search([
            ('field_id.model', '=', 'account.journal'),
            ('field_id.name', '=', 'type'),
        ])}

        journals = self.env['account.journal'].browse(x['journal_id'][0] for x in grouped_moves_to_report)
        journal_type_by_journal_id = dict(journals.mapped(lambda j: (j.id, j.type)))
        count_by_type = {}
        for group in grouped_moves_to_report:
            journal_id = group['journal_id'][0]
            journal_type = journal_type_by_journal_id[journal_id]
            count_by_type[journal_type] = count_by_type.get(journal_type, 0) + group['journal_id_count']

        return [{
            'id': f'account_journal_type.{journal_type}',
            'name': journal_type_names[journal_type],
            'type': 'integer',
            'value': count,
        } for journal_type, count in count_by_type.items()]

    @api.model
    def get_kpi_summary(self):
        result = super().get_kpi_summary()
        result.extend(self.get_account_kpi_summary())
        return result
