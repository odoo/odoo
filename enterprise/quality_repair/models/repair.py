# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv.expression import AND


class Repair(models.Model):
    _inherit = "repair.order"

    quality_check_ids = fields.One2many("quality.check", "repair_id", string="Checks")
    quality_check_todo = fields.Boolean(compute="_compute_quality_check_counts")
    quality_check_fail = fields.Boolean(compute="_compute_quality_check_counts")
    quality_alert_ids = fields.One2many('quality.alert', "repair_id", string="Alerts")
    quality_alert_count = fields.Integer(compute='_compute_quality_alert_count')

    def _compute_quality_check_counts(self):
        data = self.env['quality.check']._read_group(
            domain=[('repair_id', 'in', self.ids), ('quality_state', 'in', ['none', 'fail'])],
            groupby=['repair_id', 'quality_state'],
            aggregates=['__count'])
        mapped_data = {(repair.id, quality_state): count for repair, quality_state, count in data}
        for repair in self:
            repair.quality_check_fail = mapped_data.get((repair.id, 'fail'), 0)
            repair.quality_check_todo = mapped_data.get((repair.id, 'none'), 0)

    def _compute_quality_alert_count(self):
        data = self.env['quality.alert']._read_group(
            domain=[('repair_id', 'in', self.ids)],
            groupby=['repair_id'],
            aggregates=['__count'])
        mapped_data = {repair.id: count for repair, count in data}
        for repair in self:
            repair.quality_alert_count = mapped_data.get(repair.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._create_quality_checks_for_repair(["product", "operation"])
        return res

    def write(self, values):
        res = super().write(values)
        if "product_id" in values:
            self.quality_check_ids.filtered(lambda c: c.measure_on == "product").unlink()
            self._create_quality_checks_for_repair(["product"])
        elif "lot_id" in values:
            self.quality_check_ids.write({'lot_id': values['lot_id']})
        return res

    def _create_quality_checks_for_repair(self, measures):
        check_vals_list = []
        for measure in measures:
            points = self.env["quality.point"].sudo().search(
                self.env["quality.point"]._get_domain(
                    self.product_id, self.picking_type_id, measure_on=measure
                )
            )
            for repair in self:
                domain = self.env["quality.point"]._get_domain(
                    repair.product_id, repair.picking_type_id, measure_on=measure
                )
                for point_ids_batch in self.env.cr.split_for_in_conditions(points.ids, size=10_000):
                    # avoid fetching large HTML fields like `note` & `reason`
                    fields_to_fetch = [
                        'measure_frequency_type',
                        'measure_frequency_unit',
                        'measure_frequency_unit_value',
                        'measure_frequency_value',
                        'team_id',
                    ]
                    if len(self) > 1:
                        repair_points = self.env['quality.point'].sudo().search_fetch(
                            domain=AND([[('id', 'in', point_ids_batch)], domain]),
                            field_names=fields_to_fetch,
                        )
                    else:
                        # No need to find the intersection if there is only 1 repair,
                        # the initial set of points are valid for said repair.
                        repair_points = self.env['quality.point'].browse(point_ids_batch)
                        repair_points.fetch(fields_to_fetch)

                    for point in repair_points:
                        if point.check_execute_now():
                            check_vals_list.append({
                                "point_id": point.id,
                                "team_id": point.team_id.id,
                                "measure_on": measure,
                                "product_id": repair.product_id.id if measure == "product" else False,
                                "lot_id": repair.lot_id.id if measure == "product" else False,
                                "repair_id": repair.id,
                            })
        self.env["quality.check"].sudo().create(check_vals_list)

    def action_open_quality_checks(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.quality_check_action_main")
        action['context'] = self.env.context.copy()
        action['domain'] = [('repair_id', '=', self.id)]
        action['context'].update({
            'search_default_repair_id': [self.id],
            'default_repair_id': self.id,
        })
        return action

    def action_open_quality_alerts(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.quality_alert_action_check")
        action['context'] = {
            'default_product_id': self.product_id.id,
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_repair_id': self.id,
        }
        action['domain'] = [('repair_id', '=', self.id)]
        action['views'] = [(False, 'list'), (False, 'form')]
        if self.quality_alert_count == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.quality_alert_ids.id
        return action

    def action_check_quality(self):
        self.ensure_one()
        checks = self.quality_check_ids.filtered(lambda x: x.quality_state == 'none')
        if checks:
            return checks.action_open_quality_check_wizard()

    def action_repair_done(self):
        if any(check.quality_state == "none" for check in self.quality_check_ids):
            raise UserError(_("You still need to do the quality checks!"))
        return super().action_repair_done()

    def action_repair_cancel(self):
        res = super().action_repair_cancel()
        self.sudo().mapped("quality_check_ids").filtered(lambda c: c.quality_state == "none").unlink()
        return res
