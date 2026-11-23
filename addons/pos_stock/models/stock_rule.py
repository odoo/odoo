from odoo import api, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super()._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        self.env['pos.session']._alert_old_session()
        if use_new_cursor:
            self.env['ir.cron']._commit_progress(1)

    @api.model
    def _get_scheduler_tasks_to_do(self):
        return super()._get_scheduler_tasks_to_do() + 1

    def _get_custom_move_fields(self):
        fields = super()._get_custom_move_fields()
        if self.env['stock.move']._has_pos_order_line_access():
            fields += ['pos_order_line_ids']
        return fields

    def _push_prepare_move_copy_values(self, move_to_copy):
        vals = super()._push_prepare_move_copy_values(move_to_copy)
        if self.env['stock.move']._has_pos_order_line_access():
            vals['pos_order_line_ids'] = move_to_copy.pos_order_line_ids.ids
        return vals
