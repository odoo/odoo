# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.tools import unique
from odoo.exceptions import UserError

class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    # NOTE: `pos_config_ids` satisfies an excpeptional use case: when no PoS is specified, the loyalty program is
    # applied to every PoS. You can access the loyalty programs of a PoS using _get_program_ids() of pos.config
    pos_config_ids = fields.Many2many('pos.config', compute="_compute_pos_config_ids", store=True, readonly=False, string="Point of Sales", help="Restrict publishing to those shops.")
    pos_order_count = fields.Integer("PoS Order Count", compute='_compute_pos_order_count')
    pos_ok = fields.Boolean("Point of Sale", default=True)
    pos_report_print_id = fields.Many2one('ir.actions.report', string="Print Report", domain=[('model', '=', 'loyalty.card')], compute='_compute_pos_report_print_id', inverse='_inverse_pos_report_print_id', readonly=False,
        help="This is used to print the generated gift cards from PoS.")

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
                    raise UserError(_("You must set '%s' before setting '%s'.", mail_template_label, pos_report_print_label))
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
        query = f"""
                WITH reward_pos_order_matching AS (

                    SELECT
                    count(DISTINCT po.id) as po_ids,
                    lr.id as lr_id
                    FROM pos_order_line poline
                    JOIN pos_order po ON
                        poline.order_id = po.id
                    JOIN loyalty_reward lr ON
                        poline.reward_id IS NOT NULL
                        AND poline.reward_id = lr.id
                    GROUP BY lr_id

                    ),

                program_reward_matching AS (
                    SELECT
                    lr.id as lr_id,
                    lp.id as lp_id
                    FROM loyalty_program lp
                    JOIN loyalty_reward lr ON
                    lr.program_id = lp.id
                    WHERE lp.id  = ANY(%s)
                )

                SELECT prm.lp_id,
                SUM(rpom.po_ids)
                FROM program_reward_matching prm
                LEFT JOIN reward_pos_order_matching rpom ON
                    prm.lr_id = rpom.lr_id
                GROUP BY prm.lp_id
                """
        self._cr.execute(query, (self.ids,))
        res = self._cr.dictfetchall()
        for vals in res:
            self.filtered(lambda s: s.id == vals['lp_id']).pos_order_count = vals['sum'] or 0

    def _compute_total_order_count(self):
        super()._compute_total_order_count()
        for program in self:
            program.total_order_count += program.pos_order_count

    def action_view_pos_orders(self):
        self.ensure_one()
        pos_order_ids = list(unique(r['order_id'] for r in\
                self.env['pos.order.line'].search_read([('reward_id', 'in', self.reward_ids.ids)], fields=['order_id'])))
        return {
            'name': _("PoS Orders"),
            'view_mode': 'tree,form',
            'res_model': 'pos.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', pos_order_ids)],
            'context': dict(self._context, create=False),
        }
