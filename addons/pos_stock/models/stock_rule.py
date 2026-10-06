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
        if self.env.user.has_group('point_of_sale.group_pos_user'):
            fields += ['pos_order_line_ids']
        return fields
