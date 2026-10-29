from markupsafe import Markup

from odoo import api, fields, models


class RentalLease(models.Model):
    _name = 'rental.lease'
    _description = "Lease"
    _inherit = ['portal.mixin', 'mail.thread']
    _order = 'date_start desc'

    name = fields.Char(required=True)
    property_id = fields.Many2one('rental.property', required=True)
    tenant_id = fields.Many2one('res.partner', string="Tenant", required=True)
    company_id = fields.Many2one(related='property_id.company_id', store=True)
    date_start = fields.Date(required=True, default=fields.Date.today)
    rent_amount = fields.Float()
    state = fields.Selection([
        ('draft', "Draft"),
        ('active', "Active"),
        ('cancelled', "Cancelled"),
    ], default='draft', required=True)
    notes = fields.Text()
    property_name = fields.Char(compute='_compute_property_name')

    # Shown on the tenant's lease page so they know where to pay the rent.
    owner_bank_account = fields.Char(related='property_id.owner_bank_account')

    contract_attachment_id = fields.Many2one('ir.attachment', string="Signed Contract")
    contract_file = fields.Binary(related='contract_attachment_id.raw')

    @api.depends('property_id')
    def _compute_property_name(self):
        for lease in self:
            # Tenants have no access to the property itself; they only see its name.
            lease.property_name = lease.property_id.sudo().name

    def _compute_access_url(self):
        super()._compute_access_url()
        for lease in self:
            lease.access_url = f'/my/leases/{lease.id}'

    def action_apply_discount(self, percent):
        for lease in self:
            lease.sudo().rent_amount = lease.rent_amount * (1 - percent / 100)

    def check_access_token(self, token):
        self.ensure_one()
        return self.sudo().access_token == token

    def action_sign(self):
        for lease in self:
            lease.state = 'active'
            lease._post_signed_message()

    def _post_signed_message(self):
        for lease in self:
            lease.message_post(
                body=Markup(f"<p>Lease signed by <b>{lease.tenant_id.name}</b>.</p>"),
                **lease._prepare_notify_values(),
            )

    def _prepare_notify_values(self, partner_ids=[]):
        partner_ids.append(self.tenant_id.id)
        return {'partner_ids': partner_ids}

    def _filtered_by_rule(self, rule):
        return self.filtered(lambda lease: eval(rule, {'lease': lease}))
