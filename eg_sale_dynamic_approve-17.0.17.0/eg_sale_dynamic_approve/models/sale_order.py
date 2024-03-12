from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sale_team_id = fields.Many2one(comodel_name="sale.teams", string="Sale Approve Teams")
    sale_approve_line = fields.One2many(comodel_name="sale.approve.route", inverse_name="sale_id")

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if res.sale_team_id:
            for member_id in res.sale_team_id.team_member:
                self.env["sale.approve.route"].create({
                    "sale_id": res.id,
                    "partner_id": member_id.partner_id.id,
                    "role": member_id.role,
                    "state": "draft",
                })
        return res

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if 'sale_team_id' in vals:
            for line_id in self.sale_approve_line:
                line_id.sudo().unlink()
            if self.sale_team_id:
                for member_id in self.sale_team_id.team_member:
                    self.env["sale.approve.route"].create({
                        "sale_id": self.id,
                        "partner_id": member_id.partner_id.id,
                        "role": member_id.role,
                        "state": "draft",
                    })
        return res

    def action_confirm(self):
        if self.sale_approve_line:
            if self.sale_approve_line.filtered(lambda l: l.state != 'done'):
                raise UserError(_('%s order is not approved') % self.name)
        return super(SaleOrder, self).action_confirm()

    def approve_sale(self):
        if self.sale_approve_line:
            if self.sale_approve_line.filtered(lambda l: l.partner_id.id == self.env.user.partner_id.id):
                for line_id in self.sale_approve_line.filtered(lambda l: l.partner_id.id == self.env.user.partner_id.id):
                    line_id.write({
                        "state": "done"
                    })
            else:
                raise UserError(_("Sorry, you don't have access for Approve %s Order") % self.name)

    def disapprove_sale(self):
        if self.sale_approve_line:
            if self.sale_approve_line.filtered(lambda l: l.partner_id.id == self.env.user.partner_id.id):
                for line_id in self.sale_approve_line.filtered(lambda l: l.partner_id.id == self.env.user.partner_id.id):
                    line_id.write({
                        "state": "reject"
                    })
            else:
                raise UserError(_("Sorry, you don't have access for Disapprove %s Order") % self.name)
