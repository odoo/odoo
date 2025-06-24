# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class LoyaltyProgram(models.Model):
    _name = 'loyalty.program'
    _inherit = ['loyalty.program', 'pos.load.mixin']

    # NOTE: `pos_config_ids` satisfies an excpeptional use case: when no PoS is specified, the loyalty program is
    # applied to every PoS. You can access the loyalty programs of a PoS using _get_program_ids() of pos.config
    pos_config_ids = fields.Many2many('pos.config', compute="_compute_pos_config_ids", store=True, readonly=False, string="Point of Sales", help="Restrict publishing to those shops.")
    pos_order_count = fields.Integer("PoS Order Count", compute='_compute_pos_order_count')
    pos_ok = fields.Boolean("Point of Sale", default=True)
    pos_report_print_id = fields.Many2one('ir.actions.report', string="Print Report", domain=[('model', '=', 'loyalty.card')], compute='_compute_pos_report_print_id', inverse='_inverse_pos_report_print_id', readonly=False,
        help="This is used to print the generated gift cards from PoS.")

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        return [('id', 'in', config_id._get_program_ids().ids)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'name', 'trigger', 'applies_on', 'program_type', 'pricelist_ids', 'date_from',
            'date_to', 'limit_usage', 'max_usage', 'total_order_count', 'is_nominative',
            'portal_visible', 'portal_point_name', 'trigger_product_ids', 'rule_ids', 'reward_ids'
        ]

    @api.depends("communication_plan_ids.pos_report_print_id")
    def _compute_pos_report_print_id(self):
        for program in self:
            program.pos_report_print_id = program.communication_plan_ids.pos_report_print_id[:1]

    def _inverse_pos_report_print_id(self):
        for program in self:
            if program.program_type not in ("gift_card", "ewallet"):
                continue

            if program.pos_report_print_id:
                if not program.mail_template_id:
                    mail_template_label = program._fields.get('mail_template_id').get_description(self.env)['string']
                    pos_report_print_label = program._fields.get('pos_report_print_id').get_description(self.env)['string']
                    raise UserError(_(
                        "You must set '%(mail_template)s' before setting '%(report)s'.",
                        mail_template=mail_template_label,
                        report=pos_report_print_label,
                    ))
                else:
                    if not program.communication_plan_ids:
                        program.communication_plan_ids = self.env['loyalty.mail'].create({
                            'program_id': program.id,
                            'trigger': 'create',
                            'mail_template_id': program.mail_template_id.id,
                            'pos_report_print_id': program.pos_report_print_id.id,
                        })
                    else:
                        program.communication_plan_ids.write({
                            'trigger': 'create',
                            'pos_report_print_id': program.pos_report_print_id.id,
                        })

    @api.depends('pos_ok')
    def _compute_pos_config_ids(self):
        for program in self:
            if not program.pos_ok:
                program.pos_config_ids = False

    def _compute_pos_order_count(self):
        query = """
            SELECT program.id, SUM(orders_count)
            FROM loyalty_program program
                JOIN loyalty_reward reward ON reward.program_id = program.id
                JOIN LATERAL (
                    SELECT COUNT(DISTINCT orders.id) AS orders_count
                    FROM pos_order orders
                        JOIN pos_order_line order_lines ON order_lines.order_id = orders.id
                        WHERE order_lines.reward_id = reward.id
                ) agg ON TRUE
                WHERE program.id = ANY(%s)
                    GROUP BY program.id
                """
        self._cr.execute(query, (self.ids,))
        res = self._cr.dictfetchall()
        res = {k['id']: k['sum'] for k in res}

        for rec in self:
            rec.pos_order_count = res.get(rec.id) or 0

    def _compute_total_order_count(self):
        super()._compute_total_order_count()
        for program in self:
            program.total_order_count += program.pos_order_count
