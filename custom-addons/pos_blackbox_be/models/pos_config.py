# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from odoo.osv.expression import OR
from odoo.service.common import exp_version


class PosConfig(models.Model):
    _inherit = "pos.config"

    iface_fiscal_data_module = fields.Many2one(
        "iot.device",
        domain="[('type', '=', 'fiscal_data_module'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    certified_blackbox_identifier = fields.Char(
        "Blackbox Identifier",
        store=True,
        compute="_compute_certified_pos",
        readonly=True,
    )
    pos_version = fields.Char('Odoo Version', compute='_compute_odoo_version')

    def _compute_odoo_version(self):
        self.pos_version = exp_version()['server_serie']

    @api.depends("iface_fiscal_data_module")
    def _compute_certified_pos(self):
        if self.iface_fiscal_data_module:
            self.certified_blackbox_identifier = self.iface_fiscal_data_module.name[
                -14:
            ]
            self.env["pos_blackbox_be.log"].sudo().create([{
                "action": "create",
                "model_name": self._name,
                "record_name": self.name,
                "description": "Session started with: %s" % self.certified_blackbox_identifier,
            }])
            if not self.env['ir.sequence'].search([('code', '=', f'pos_blackbox_be.NS_blackbox_{self.certified_blackbox_identifier}')]):
                self.env['ir.sequence'].sudo().create({
                    'name': _("NS Order by blackbox"),
                    'padding': 4,
                    'code': f'pos_blackbox_be.NS_blackbox_{self.certified_blackbox_identifier}',
                    'company_id': self.company_id.id,
                })
                self.env['ir.sequence'].sudo().create({
                    'name': _("PS Order by blackbox"),
                    'padding': 4,
                    'code': f'pos_blackbox_be.PS_blackbox_{self.certified_blackbox_identifier}',
                    'company_id': self.company_id.id,
                })

    def _check_is_certified_pos(self):
        if self.certified_blackbox_identifier and not self.iface_fiscal_data_module:
            raise UserError(
                _("Forbidden to start a certified Point of sale without blackbox")
            )

    @api.depends("iface_fiscal_data_module")
    def _compute_iot_device_ids(self):
        super(PosConfig, self)._compute_iot_device_ids()
        for config in self:
            if config.is_posbox:
                config.iot_device_ids += config.iface_fiscal_data_module

    def _check_before_creating_new_session(self):
        self._check_is_certified_pos()
        if self.iface_fiscal_data_module:
            self._check_self_order()
            self._check_loyalty()
            self._check_insz_user()
            self._check_company_address()
            self._check_work_product_taxes()
            self._check_employee_insz_or_bis_number()
            self._check_pos_category()
            self._check_cash_rounding()
            self._check_printer_connected()
            self._check_floor_plan_ids()
            self._check_is_table()
        return super(PosConfig, self)._check_before_creating_new_session()

    def _check_self_order(self):
        for config in self:
            if (
                self.env['ir.module.module'].search([('name', '=', 'pos_self_order'), ('state', '=', 'installed')]) and config.self_ordering_mode not in ['nothing', 'consultation']
            ):
                raise UserError(
                    _(
                        'Certified blackbox are not compatible with the self-ordering mode ("QR menu + Ordering" and "Kiosk") for the moment. Please disable it.'
                    )
                )

    def _check_loyalty(self):
        for config in self:
            if (
                self.env['ir.module.module'].search([('name', '=', 'pos_loyalty'), ('state', '=', 'installed')]) and config._get_program_ids()
            ):
                raise UserError(
                    _(
                        "Loyalty programs and gift card cannot be used on a PoS associated with a blackbox."
                    )
                )

    def _check_work_product_taxes(self):
        work_in = self.env.ref("pos_blackbox_be.product_product_work_in")
        work_out = self.env.ref("pos_blackbox_be.product_product_work_out")
        if (
            not work_in.taxes_id
            or work_in.taxes_id.amount != 0
            or not work_out.taxes_id
            or work_out.taxes_id.amount != 0
        ):
            raise ValidationError(
                _("The WORK IN/OUT products must have a taxes with 0%.")
            )

    def _check_insz_user(self):
        if not self.env.user.insz_or_bis_number:
            raise ValidationError(_("The user must have a INSZ or BIS number."))

    def _check_company_address(self):
        if not self.company_id.street:
            raise ValidationError(_("The address of the company must be filled."))
        if not self.company_id.company_registry:
            raise ValidationError(_("The VAT number of the company must be filled."))

    def _check_pos_category(self):
        if self.limit_categories:
            if (
                self.env.ref("pos_blackbox_be.pos_category_fdm").id
                not in self.iface_available_categ_ids.ids
            ):
                raise ValidationError(
                    _(
                        "You have to add the fiscal category to the limited category in order to use the fiscal data module"
                    )
                )

    def _check_is_table(self):
        if self.iface_fiscal_data_module and self.module_pos_restaurant:
            if not self.floor_ids:
                raise ValidationError(_("You must link at least 1 floor to the configuration in order to use the fiscal data module."))
            for floor in self.floor_ids:
                if floor.table_ids:
                    return
            raise ValidationError(_("You must link at least 1 table to the configuration in order to use the fiscal data module."))

    @api.constrains("iface_fiscal_data_module", "fiscal_position_ids")
    def _check_posbox_fp_tax_code(self):
        invalid_tax_lines = [
            (fp.name, tax_line.tax_dest_id.name)
            for config in self
            for fp in config.fiscal_position_ids
            for tax_line in fp.tax_ids
            if (
                    tax_line.tax_src_id.identification_letter
                    and not tax_line.tax_dest_id.identification_letter
            )
        ]

        if invalid_tax_lines:
            raise ValidationError(
                "Fiscal Position %s (tax %s) has an invalid tax amount. Only 21%%, 12%%, 6%% and 0%% are allowed." %
                invalid_tax_lines[0]
            )

    @api.constrains('iface_fiscal_data_module', 'floor_ids')
    def _check_floor_plan_ids(self):
        if self.iface_fiscal_data_module and self.floor_ids:
            for floor in self.floor_ids:
                if len(floor.pos_config_ids) > 1:
                    raise ValidationError("Floor plans cannot be shared in different POS configurations when using the Blackbox module.")

    def _check_employee_insz_or_bis_number(self):
        for config in self:
            if config.module_pos_hr:
                all_employee_ids = self.env['hr.employee'].search(self._employee_domain(self.env.uid))
                emp_names = [emp.name for emp in all_employee_ids if not emp.sudo().insz_or_bis_number] + ([self.env.user.name] if not self.env.user.employee_id.insz_or_bis_number else [])

                if len(emp_names) > 0:
                    raise ValidationError(
                        _("%s must have an INSZ or BIS number.", ", ".join(emp_names))
                    )

    def _check_cash_rounding(self):
        if not self.cash_rounding:
            raise ValidationError(_("Cash rounding must be enabled"))
        if (
            self.rounding_method.rounding != 0.05
            or self.rounding_method.rounding_method != "HALF-UP"
        ):
            raise ValidationError(
                _("The rounding method must be set to 0.5 and HALF-UP")
            )

    def _check_printer_connected(self):
        epson_printer = False
        if hasattr(self, "epson_printer_ip"):
            epson_printer = self.epson_printer_ip
        if not self.iface_printer_id and not epson_printer:
            raise ValidationError(_("A printer must be connected"))
        if not self.iface_print_auto:
            raise ValidationError(_("Automatic Receipt Printing must be activated"))
        if not self.iface_print_skip_screen:
            raise ValidationError(_("Skip Preview Screen must be activated"))

    def _get_work_products(self):
        empty_product = self.env['product.product']
        work_in_product = self.env.ref('pos_blackbox_be.product_product_work_in', raise_if_not_found=False) or empty_product
        work_out_product = self.env.ref('pos_blackbox_be.product_product_work_out', raise_if_not_found=False) or empty_product
        return work_in_product | work_out_product

    def _get_special_products(self):
        return super()._get_special_products() | self._get_work_products()

    def _get_available_product_domain(self):
        domain = super()._get_available_product_domain()
        if work_products := self._get_work_products():
            return OR([domain, [('id', 'in', work_products.ids)]])
        return domain

    def get_NS_sequence_next(self):
        return self.env['ir.sequence'].next_by_code(f'pos_blackbox_be.NS_blackbox_{self.certified_blackbox_identifier}')

    def get_PS_sequence_next(self):
        return self.env['ir.sequence'].next_by_code(f'pos_blackbox_be.PS_blackbox_{self.certified_blackbox_identifier}')
