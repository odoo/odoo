# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class RentalSign(models.TransientModel):
    _name = "rental.sign.wizard"
    _description = "Sign Documents from a SO"

    @api.model
    def default_get(self, fields):
        res = super(RentalSign, self).default_get(fields)
        if 'template_id' in fields:
            company = self.env['sale.order'].browse(res.get('order_id')).company_id or self.env.company
            default_template = company.rental_sign_tmpl_id
            # if document not properly accessible by all employees, avoid access error
            if default_template.has_access("read"):
                res["template_id"] = company.rental_sign_tmpl_id.id
        return res

    template_id = fields.Many2one(
        "sign.template", "Document Template", required=True, ondelete="cascade"
    )
    order_id = fields.Many2one(
        "sale.order", "Sales Order", required=True, ondelete="cascade",
        default=lambda s: s.env.context.get("active_id", None),
    )

    def next_step(self):
        pending_sign_request = self.order_id.sign_request_ids.filtered(
            lambda request: request.template_id == self.template_id
            and request.state == "sent"
        )
        if pending_sign_request:
            return pending_sign_request.go_to_document()
        else:
            action = self.env['ir.actions.act_window']._for_xml_id('sign.action_sign_send_request')
            action["context"] = {
                "active_id": self.template_id.id,
                "sign_directly_without_mail": True,
                "default_res_model": "sale.order",
                "default_res_id": self.order_id.id,
                "default_reference_doc": f"sale.order,{self.order_id.id}",
                "default_signer_id": self.order_id.partner_id.id
            }
            return action
