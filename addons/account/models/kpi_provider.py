from odoo import api, fields, models


class KpiProvider(models.AbstractModel):
    _inherit = 'kpi.provider'

    @api.model
    def get_account_kpi_summary(self):
        grouped_moves_to_report = self.env['account.move']._read_group(
            fields.Domain.OR([
                [('state', '=', 'draft')],
                [('state', '=', 'posted'), ('checked', '=', False)],
                [('state', '=', 'posted'), ('journal_id.type', '=', 'bank'), ('statement_line_id.is_reconciled', '=', False)],
            ]),
            ['journal_id'],
            ['journal_id:count'],
        )

        FieldsSelection = self.env['ir.model.fields.selection'].with_context(lang=self.env.user.lang)
        journal_type_names = {x.value: x.name for x in FieldsSelection.search([
            ('field_id.model', '=', 'account.journal'),
            ('field_id.name', '=', 'type'),
        ])}

        count_by_type = {}
        for journal_id, count in grouped_moves_to_report:
            journal_type = journal_id.type
            count_by_type[journal_type] = count_by_type.get(journal_type, 0) + count

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
