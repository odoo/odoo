from odoo import api, models


class KpiProvider(models.AbstractModel):
    _inherit = 'kpi.provider'

    @api.model
    def get_account_kpi_summary(self):
        AccountMove = self.env['account.move']
        grouped_draft_moves = AccountMove._read_group([('state', '=', 'draft')], ['move_type'], ['move_type:count'])

        FieldsSelection = self.env['ir.model.fields.selection'].with_context(lang=self.env.user.lang)
        move_type_names = {x.value: x.name for x in FieldsSelection.search([
            ('field_id.model', '=', 'account.move'),
            ('field_id.name', '=', 'move_type'),
        ])}

        return [{
            'id': f'account_move_type.{move_type}',
            'name': move_type_names[move_type],
            'type': 'integer',
            'value': count,
        } for move_type, count in grouped_draft_moves]

    @api.model
    def get_kpi_summary(self):
        result = super().get_kpi_summary()
        result.extend(self.get_account_kpi_summary())
        return result
