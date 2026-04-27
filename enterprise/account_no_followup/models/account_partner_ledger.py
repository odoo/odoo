from odoo import api, models
from odoo.tools import SQL


class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    @api.model
    def action_toggle_no_followup(self, line_id, all_line_ids):
        """Toggle the `no_followup` field on the journal item corresponding to the given `line_id`.

        Toggling this field may result in other journal items of the same report having their field toggled as well.
        This function will return all impacted lines, so the report can be updated dynamically.

        :param line_id: The report line ID.
        :param all_line_ids: A list containing all the report's line IDs.
        :return: A dict containing:
            - `updated_value`: the updated `no_followup` value (`True` or `False`)
            - `updated_line_ids`: a list of the impacted report lines
        """
        model, aml_id = self.env['account.report']._get_model_info_from_id(line_id)
        if model != 'account.move.line':
            return None
        aml = self.env['account.move.line'].browse(aml_id)
        aml.no_followup = not aml.no_followup

        aml_id_to_line_id = {}
        for cur_line_id in all_line_ids:
            model, record_id = self.env['account.report']._get_model_info_from_id(cur_line_id)
            if model == 'account.move.line':
                aml_id_to_line_id[record_id] = cur_line_id

        res = {'updated_value': aml.no_followup, 'updated_line_ids': [aml_id_to_line_id[aml.id]]}
        move = aml.move_id
        if move.is_invoice():
            # For invoices, the `no_followup` toggle will impact all its receivable/payable lines.
            res['updated_line_ids'] = move.line_ids.filtered(
                lambda line: line.account_type in ('asset_receivable', 'liability_payable'),
            ).mapped(lambda line: aml_id_to_line_id[line.id])
        return res

    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        line = super()._get_report_line_move_line(options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift)
        line['no_followup'] = aml_query_result['no_followup']
        return line

    def _get_aml_value_extra_select(self):
        return super()._get_aml_value_extra_select() + [
            SQL(', account_move_line.no_followup')
        ]
