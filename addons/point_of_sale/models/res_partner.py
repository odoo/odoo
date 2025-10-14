# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'pos.load.mixin']

    pos_order_count = fields.Integer(
        compute='_compute_pos_order',
        help="The number of point of sales orders related to this customer",
        groups="point_of_sale.group_pos_user",
    )
    pos_order_ids = fields.One2many('pos.order', 'partner_id', readonly=True)
    pos_contact_address = fields.Char('PoS Address', compute='_compute_contact_address')
    invoice_emails = fields.Char(compute='_compute_invoice_emails', readonly=True)

    def _compute_contact_address(self):
        super()._compute_contact_address()
        for partner in self:
            partner.pos_contact_address = partner._display_address(without_company=True)

    @api.model
    def get_new_partner(self, config_id, domain, offset):
        config = self.env['pos.config'].browse(config_id)
        if len(domain) == 0:
            limited_partner_ids = {partner[0] for partner in config.get_limited_partners_loading(offset)}
            domain += [('id', 'in', list(limited_partner_ids))]
            new_partner = self.search_read(domain, self._load_pos_data_fields(config_id), load=False)
        else:
            # If search domain is not empty, we need to search inside all partners
            new_partner = self.search_read(domain, self._load_pos_data_fields(config_id), offset=offset, limit=100, load=False)
        return {
            'res.partner': new_partner,
        }

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = self.env['pos.config'].browse(data['pos.config'][0]['id'])

        # Collect partner IDs from loaded orders
        loaded_order_partner_ids = {order['partner_id'] for order in data['pos.order']}

        # Extract partner IDs from the tuples returned by get_limited_partners_loading
        limited_partner_ids = {partner[0] for partner in config_id.get_limited_partners_loading()}

        limited_partner_ids.add(self.env.user.partner_id.id)  # Ensure current user is included
        partner_ids = limited_partner_ids.union(loaded_order_partner_ids)
        return [('id', 'in', list(partner_ids))]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'id', 'name', 'street', 'street2', 'city', 'state_id', 'country_id', 'vat', 'lang', 'phone', 'zip', 'email',
            'barcode', 'write_date', 'property_account_position_id', 'property_product_pricelist', 'parent_name',
            'pos_contact_address', 'invoice_emails', 'company_type'
        ]

    def _compute_pos_order(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )
        pos_order_data = self.env['pos.order']._read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            groupby=['partner_id'], aggregates=['__count']
        )
        self_ids = set(self._ids)

        self.pos_order_count = 0
        for partner, count in pos_order_data:
            while partner:
                if partner.id in self_ids:
                    partner.pos_order_count += count
                partner = partner.parent_id

    @api.depends('email', 'child_ids.type', 'child_ids.email')
    def _compute_invoice_emails(self):
        for record in self:
            emails = [record.email] if record.email else []
            emails.extend([child.email for child in record.child_ids if child.type == "invoice" and child.email])
            record.invoice_emails = ', '.join(emails) if emails else ''

    def action_view_pos_order(self):
        '''
        This function returns an action that displays the pos orders from partner.
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('point_of_sale.action_pos_pos_form')
        if self.is_company:
            action['domain'] = [('partner_id.commercial_partner_id', '=', self.id)]
        else:
            action['domain'] = [('partner_id', '=', self.id)]
        return action

    def open_commercial_entity(self):
        return {
            **super().open_commercial_entity(),
            **({'target': 'new'} if self.env.context.get('target') == 'new' else {}),
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_if_pos_no_orders(self):
        if any(self.mapped('pos_order_ids')):
            raise ValidationError(_('You cannot delete a customer that has point of sales orders. You can archive it instead.'))
