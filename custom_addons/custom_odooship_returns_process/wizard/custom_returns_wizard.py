# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

import json
import logging
from odoo import models,fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import requests


_logger = logging.getLogger(__name__)

class ReturnsScanWizard(models.TransientModel):
    _name = "returns.scan.wizard"
    _description = "Returns Scan Wizard"

    picking_id = fields.Many2one('stock.picking', required=True, readonly=True)
    scan_product_barcode = fields.Char(string="Scan Product Barcode")
    line_ids = fields.One2many('returns.scan.wizard.line', 'wizard_id', string="Products")
    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        store=True
    )
    site_code_id = fields.Many2one('site.code.configuration', string='Site Code', store=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            picking = self.env['stock.picking'].browse(active_id)
            if picking and picking.exists():
                res['tenant_code_id'] = picking.tenant_code_id.id if picking.tenant_code_id else False
                res['site_code_id'] = picking.site_code_id.id if picking.site_code_id else False
        return res

    @api.onchange('scan_product_barcode')
    def _onchange_scan_product_barcode(self):
        scanned_input = (self.scan_product_barcode or "").strip()
        if not scanned_input:
            return

        tenant_id = self.tenant_code_id.name
        site_id = self.site_code_id.name
        picking_id = self.picking_id.id

        if not tenant_id or not site_id or not picking_id:
            raise ValidationError(_("Tenant, Site and Picking must be selected before scanning."))

        # Find valid products for this picking
        valid_move_products = self.env['stock.move'].search([
            ('picking_id', '=', picking_id)
        ]).mapped('product_id')
        valid_product_ids = set(valid_move_products.ids)

        # 1. Search product by barcode and tenant match
        product = self.env['product.product'].search([
            ('barcode', '=', scanned_input),
            ('tenant_id', '=', tenant_id)
        ], limit=1)

        # 2. Try multi-barcode model (if you use it)
        if not product:
            multi_barcode = self.env['product.barcode.multi'].search([
                ('name', '=', scanned_input),
                ('product_id.tenant_id', '=', tenant_id)
            ], limit=1)
            if multi_barcode:
                product = multi_barcode.product_id

        if not product:
            raise ValidationError(("No product found for scanned code: %s") % scanned_input)

        if product.id not in valid_product_ids:
            raise ValidationError((
                "Scanned product '%s' is not included in the current picking."
            ) % product.display_name)

        # Find wizard lines for this product
        matching_lines = self.line_ids.filtered(lambda l: l.product_id.id == product.id)
        if not matching_lines:
            raise ValidationError(("Scanned SKU '%s' is not in this return list.") % (product.default_code or product.name))

        # Mark first unscanned line as scanned (or all lines as per your logic)
        unscanned_line = matching_lines.filtered(lambda l: not l.scanned)
        if not unscanned_line:
            raise ValidationError(("All units of SKU '%s' have already been scanned.") % (product.default_code or product.name))

        # Mark as scanned
        unscanned_line[0].scanned = True

        # Optionally clear the barcode field for next scan
        self.scan_product_barcode = ""

    def button_validate_and_send(self):
        """
        Send product lines to the API endpoint for this wizard's lines.
        Include all lines, with 'scanned': true/false for each.
        """
        self.ensure_one()

        if not self.tenant_code_id or not self.site_code_id:
            raise ValidationError(_("Tenant Code and Site Code must be specified for this operation."))

        if not self.line_ids:
            raise ValidationError(_("No product lines found in the wizard."))

        product_lines = []
        stock_quant_obj = self.env['stock.quant']
        for line in self.line_ids:
            line.remaining_qty = line.qty if line.scanned else 0
            qty_to_send = line.remaining_qty
            if line.scanned:
                if not line.product_grade:
                    raise ValidationError(_("Please select Product Grade for '%s'.") % line.product_id.display_name)
                if line.product_grade != 'grade_a' and not line.grade_reason_id:
                    raise ValidationError(_("Grade Reason is required for product '%s' with grade '%s'.") %
                                          (line.product_id.display_name,
                                           dict(line._fields['product_grade'].selection).get(line.product_grade,line.product_grade)))
            if not line.scanned:
                if not line.grade_reason_id:
                    raise ValidationError(
                        _("Grade Reason is required for unreturned product '%s'.") % line.product_id.display_name)
            product_lines.append({
                "product_id": line.product_id.default_code,
                "name": line.product_id.name,
                "product_uom_qty": line.qty,
                "quantity": qty_to_send,
                "product_grade": line.product_grade or "",
                "summary": line.summary or "",
                "sellable_non_sellable": line.sellable_non_sellable,
                "grade_reason": line.grade_reason_id.description if line.grade_reason_id else "",
                "scanned": bool(line.scanned),
            })
            if line.scanned and line.qty:
                stock_quant_obj._update_available_quantity(
                    product_id=line.product_id,
                    location_id=self.picking_id.location_dest_id,
                    quantity=line.qty,
                )
            move = self.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id.id == line.product_id.id and m.line_number == line.line_number
            )
            for m in move:
                m.remaining_qty = 0 if line.scanned else line.qty
                m.quantity = line.qty if line.scanned else 0
        schedule_date = self.picking_id.scheduled_date.strftime("%d-%m-%Y") if self.picking_id.scheduled_date else "N/A"
        current_date = date.today().strftime("%d-%m-%Y")

        payload = {
            "receipt_number": self.picking_id.name,
            "partner_id": self.picking_id.partner_id.name,
            "tenant_code": self.tenant_code_id.name,
            "site_code": self.site_code_id.name,
            "origin": self.picking_id.origin or "N/A",
            "product_lines": product_lines,
            "schedule_date": schedule_date,
            "current_date": current_date,
            "reference_1": self.picking_id.reference_1,
        }

        json_data = json.dumps(payload, indent=4)
        _logger.info(f"Sending payload: {json_data}")

        self.picking_id.state = 'done'
        _logger.info(f"Picking {self.picking_id.name} marked as done.")

        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
        if is_production == 'True':
            api_url = (
                "https://shiperoo-connect-fp.prod.automation.shiperoo.com/"
                "sc-file-processor/api/return-completion"
            )
            auth = ('apiuser', 'd7oX8L3af6D4FDobC8AFsWRgLamvQs')
        else:
            api_url = (
                "https://shiperoo-connect.uat.automation.shiperoo.com/"
                "sc-file-processor/api/return-completion"
            )
            auth = ('apiuser', 'apipass')

        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(api_url, headers=headers, data=json_data, auth=auth)
            _logger.info(f"Response Status Code: {response.status_code}, Response Body: {response.text}")

            if response.status_code != 200:
                raise UserError(f"Failed to send data: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error communicating with API: {str(e)}")
            raise UserError(f"Error communicating with API: {str(e)}")

        # If no errors, update the state to 'done'
        self.picking_id.state = 'done'
        _logger.info(f"Picking {self.picking_id.name} marked as done.")

        return {'type': 'ir.actions.act_window_close'}


class ReturnsScanWizardLine(models.TransientModel):
    _name = "returns.scan.wizard.line"
    _description = "Returns Scan Wizard Line"

    wizard_id = fields.Many2one('returns.scan.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    name = fields.Char(related= 'product_id.default_code', readonly=True)
    qty = fields.Float(string="Quantity", readonly=True)
    product_grade = fields.Selection([
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C')
    ],string='Product Grade')
    sellable_non_sellable = fields.Selection(
        [('sellable', 'Sellable'),
         ('non_sellable', 'Non-Sellable')], string='Sellable or Non Sellable'
    )
    summary = fields.Char(string="Summary")
    grade_reason_id = fields.Many2one(
        'grade.message.configuration',
        string='Grade Reason',
        domain="[('product_grade', '=', product_grade)]",
    )
    remaining_qty = fields.Float(string="Remaining Qty", readonly=True)
    scanned = fields.Boolean(string="Scanned", default=False)
    line_number = fields.Integer(string='Return Line Number')

    @api.onchange('scanned', 'sellable_non_sellable')
    def _onchange_scanned_or_qty(self):
        for line in self:
            line.remaining_qty = 0 if line.scanned else line.qty

    @api.onchange('product_grade')
    def onchange_product_grade(self):
        for line in self:
            if line.product_grade == 'grade_a':
                line.sellable_non_sellable = 'sellable'
                line.grade_reason_id = False
            if line.product_grade != 'grade_a':
                line.sellable_non_sellable = 'non_sellable'
