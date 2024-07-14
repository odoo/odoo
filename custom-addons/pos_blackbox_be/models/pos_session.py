# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
from itertools import groupby
from collections import Counter


class pos_session(models.Model):
    _inherit = "pos.session"

    total_base_of_measure_tax_a = fields.Monetary(compute="_compute_total_tax")
    total_base_of_measure_tax_b = fields.Monetary(compute="_compute_total_tax")
    total_base_of_measure_tax_c = fields.Monetary(compute="_compute_total_tax")
    total_base_of_measure_tax_d = fields.Monetary(compute="_compute_total_tax")

    cash_box_opening_number = fields.Integer(
        help="Count the number of cashbox opening during the session"
    )
    users_clocked_ids = fields.Many2many(
        "res.users",
        "users_session_clocking_info",
        string="Users Clocked In",
        help="This is a technical field used for tracking the status of the session for each users.",
    )
    employees_clocked_ids = fields.Many2many(
        "hr.employee",
        "employees_session_clocking_info",
        string="Employees Clocked In",
        help="This is a technical field used for tracking the status of the session for each employees.",
    )

    pro_forma_sales_number = fields.Integer()
    pro_forma_sales_amount = fields.Monetary()
    pro_forma_refund_number = fields.Integer()
    pro_forma_refund_amount = fields.Monetary()

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        loaded_data["product_product_work_in"] = self.env.ref(
            "pos_blackbox_be.product_product_work_in"
        ).id
        loaded_data["product_product_work_out"] = self.env.ref(
            "pos_blackbox_be.product_product_work_out"
        ).id

    def _loader_params_res_users(self):
        result = super()._loader_params_res_users()
        result["search_params"]["fields"].append("insz_or_bis_number")
        return result

    def _loader_params_pos_session(self):
        result = super()._loader_params_pos_session()
        result["search_params"]["fields"].append("users_clocked_ids")
        result["search_params"]["fields"].append("employees_clocked_ids")
        return result

    def _loader_params_res_company(self):
        result = super()._loader_params_res_company()
        result["search_params"]["fields"].append("street")
        return result

    def _get_pos_ui_hr_employee(self, params):
        result = super()._get_pos_ui_hr_employee(params)
        employee_ids = [employee['id'] for employee in result]
        employees_insz_or_bis_number = self.env['hr.employee'].sudo().browse(employee_ids).read(['insz_or_bis_number'])
        insz_or_bis_number_per_employee_id = {employee['id']: employee['insz_or_bis_number'] for employee in employees_insz_or_bis_number}
        for employee in result:
            employee['insz_or_bis_number'] = insz_or_bis_number_per_employee_id[employee['id']]
        return result

    def _loader_params_account_tax(self):
        result = super()._loader_params_account_tax()
        result["search_params"]["fields"].append("identification_letter")
        return result

    @api.depends("order_ids")
    def _compute_total_tax(self):
        for session in self:
            session.total_base_of_measure_tax_a = 0
            session.total_base_of_measure_tax_b = 0
            session.total_base_of_measure_tax_c = 0
            session.total_base_of_measure_tax_d = 0
            for order in session.order_ids:
                session.total_base_of_measure_tax_a += order.blackbox_tax_category_a
                session.total_base_of_measure_tax_b += order.blackbox_tax_category_b
                session.total_base_of_measure_tax_c += order.blackbox_tax_category_c
                session.total_base_of_measure_tax_d += order.blackbox_tax_category_d

    @api.depends("order_ids")
    def _compute_amount_of_vat_tickets(self):
        for rec in self:
            rec.amount_of_vat_tickets = len(rec.order_ids)

    def get_user_session_work_status(self, user_id):
        return ((self.config_id.module_pos_hr and user_id in self.employees_clocked_ids.ids) or
            (not self.config_id.module_pos_hr and user_id in self.users_clocked_ids.ids))

    def increase_cash_box_opening_counter(self):
        self.cash_box_opening_number += 1

    def set_user_session_work_status(self, user_id, status):
        context = (
            "employees_clocked_ids"
            if self.config_id.module_pos_hr
            else "users_clocked_ids"
        )
        if status:
            self.write({context: [(4, user_id)]})
        else:
            self.write({context: [(3, user_id)]})
        return self[context].ids

    def _get_sequence_number(self):
        if self.state == "closed":
            return self.env["ir.sequence"].next_by_code(
                "report.point_of_sale.report_saledetails.sequenceZUser"
            )
        return self.env["ir.sequence"].next_by_code(
            "report.point_of_sale.report_saledetails.sequenceXUser"
        )

    def _get_user_report_data(self):
        def sorted_key_insz(order):
            order.ensure_one()
            if order.employee_id:
                insz = order.sudo().employee_id.insz_or_bis_number
            else:
                insz = order.user_id.insz_or_bis_number
            return [insz, order.date_order]

        def groupby_key_insz(order):
            if order.employee_id:
                insz = order.sudo().employee_id.insz_or_bis_number
            else:
                insz = order.user_id.insz_or_bis_number
            return [insz]

        data = {}
        if not self.config_id.certified_blackbox_identifier:
            return data

        currency = self.currency_id

        work_in = self.env.ref("pos_blackbox_be.product_product_work_in").id
        work_out = self.env.ref("pos_blackbox_be.product_product_work_out").id

        for k, g in groupby(sorted(self.order_ids, key=sorted_key_insz), key=groupby_key_insz):
            i = 0
            insz = k[0]
            data[insz] = []
            for order in g:
                if order.lines and order.lines[0].product_id.id == work_in:
                    data[insz].append({
                        'login': order.employee_id.name if order.employee_id else order.user_id.name,
                        'insz_or_bis_number': order.sudo().employee_id.insz_or_bis_number if order.employee_id else order.user_id.insz_or_bis_number,
                        'revenue': 0,
                        'revenue_per_category': Counter(),
                        'first_ticket_time': order.date_order,
                        'last_ticket_time': False,
                        'fdmIdentifier': order.config_id.certified_blackbox_identifier,
                        'cash_rounding_applied': 0,
                    })

                data[insz][i]['revenue'] += order.amount_paid
                data[insz][i]['cash_rounding_applied'] += round(order.amount_total - order.amount_paid, currency.decimal_places)
                total_sold_per_category = {}
                for line in order.lines:
                    category_names = line.product_id.pos_categ_ids.mapped('name') or ["None"]
                    for category_name in category_names:
                        if category_name not in total_sold_per_category:
                            total_sold_per_category[category_name] = 0
                        total_sold_per_category[category_name] += round(line.price_subtotal_incl, currency.decimal_places)

                data[insz][i]['revenue_per_category'].update(Counter(total_sold_per_category))

                if order.lines and order.lines[0].product_id.id == work_out:
                    data[insz][i]['last_ticket_time'] = order.date_order
                    i = i + 1
        for user in data.values():
            for session in user:
                session['revenue_per_category'] = list(session['revenue_per_category'].items())
        return data

    def action_report_journal_file(self):
        self.ensure_one()
        pos = self.config_id
        if not pos.iface_fiscal_data_module:
            raise UserError(_("PoS %s is not a certified PoS", pos.name))
        return {
            "type": "ir.actions.act_url",
            "url": "/journal_file/" + str(pos.certified_blackbox_identifier),
            "target": "self",
        }

    def _get_total_correction(self):
        total_corrections = 0

        for order in self.order_ids:
            if order.amount_total > 0:
                for line in order.lines:
                    if line.price_subtotal_incl < 0:
                        total_corrections += line.price_subtotal_incl

        return round(total_corrections, self.currency_id.decimal_places)

    def _update_pro_forma(self, order, custom_data=None):
        self.ensure_one()
        if order.state == "draft":
            amount_total = order.amount_total
            if custom_data:
                amount_total = custom_data.get("amount_total", amount_total)
            if amount_total < 0:
                self.pro_forma_refund_number += 1
                self.pro_forma_refund_amount += round(amount_total, self.currency_id.decimal_places)
            else:
                self.pro_forma_sales_number += 1
                self.pro_forma_sales_amount += round(amount_total, self.currency_id.decimal_places)

    def get_total_discount_positive_negative(self, positive):
        order_ids = self.order_ids.ids
        price_operator = ">=" if positive else "<"

        orderlines = self.env["pos.order.line"].search(
            [("order_id", "in", order_ids), ("price_subtotal_incl", price_operator, 0), ("discount", ">", 0)]
        )

        tax_amounts = sum(line.qty * line.price_unit / 100 * line.tax_ids.amount for line in orderlines)

        amount = sum(
            line.qty * line.price_unit - line.price_subtotal_incl + tax_amounts
            for line in orderlines
        )

        return round(amount, self.currency_id.decimal_places)

    def check_everyone_is_clocked_out(self):
        if (
            self.config_id.module_pos_hr and len(self.employees_clocked_ids.ids) > 0
        ) or (
            not self.config_id.module_pos_hr and len(self.users_clocked_ids.ids) > 0
        ):
            raise UserError(_("You cannot close the POS with employees still clocked in. Please clock them out first."))
