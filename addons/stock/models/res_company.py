# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import threading

from odoo import _, api, fields, models


class Company(models.Model):
    _inherit = "res.company"
    _check_company_auto = True

    def _default_confirmation_mail_template(self):
        try:
            return self.env.ref('stock.mail_template_data_delivery_confirmation').id
        except ValueError:
            return False

    # used for resupply routes between warehouses that belong to this company
    internal_transit_location_id = fields.Many2one(
        'stock.location', 'Internal Transit Location', ondelete="restrict", check_company=True)
    stock_move_email_validation = fields.Boolean("Email Confirmation picking", default=False)
    stock_mail_confirmation_template_id = fields.Many2one('mail.template', string="Email Template confirmation picking",
        domain="[('model', '=', 'stock.picking')]",
        default=_default_confirmation_mail_template,
        help="Email sent to the customer once the order is done.")
    annual_inventory_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Annual Inventory Month',
        default='12',
        help="Annual inventory month for products not in a location with a cyclic inventory date. Set to no month if no automatic annual inventory.")
    annual_inventory_day = fields.Integer(
        string='Day of the month', default=31,
        help="""Day of the month when the annual inventory should occur. If zero or negative, then the first day of the month will be selected instead.
        If greater than the last day of a month, then the last day of the month will be selected instead.""")

    def _create_transit_location(self):
        '''Create a transit location with company_id being the given company_id. This is needed
           in case of resuply routes between warehouses belonging to the same company, because
           we don't want to create accounting entries at that time.
        '''
        parent_location = self.env.ref('stock.stock_location_locations', raise_if_not_found=False)
        for company in self:
            location = self.env['stock.location'].create({
                'name': _('Inter-warehouse transit'),
                'usage': 'transit',
                'location_id': parent_location and parent_location.id or False,
                'company_id': company.id,
                'active': False
            })

            company.write({'internal_transit_location_id': location.id})

            company.partner_id.with_company(company).write({
                'property_stock_customer': location.id,
                'property_stock_supplier': location.id,
            })

    def _create_inventory_loss_location(self):
        parent_location = self.env.ref('stock.stock_location_locations_virtual', raise_if_not_found=False)
        for company in self:
            inventory_loss_location = self.env['stock.location'].create({
                'name': 'Inventory adjustment',
                'usage': 'inventory',
                'location_id': parent_location.id,
                'company_id': company.id,
            })
            self.env['ir.default'].set('product.template', 'property_stock_inventory', inventory_loss_location.id, company_id=company.id)

    def _create_production_location(self):
        parent_location = self.env.ref('stock.stock_location_locations_virtual', raise_if_not_found=False)
        for company in self:
            production_location = self.env['stock.location'].create({
                'name': 'Production',
                'usage': 'production',
                'location_id': parent_location.id,
                'company_id': company.id,
            })
            self.env['ir.default'].set('product.template', 'property_stock_production', production_location.id, company_id=company.id)

    def _create_scrap_location(self):
        parent_location = self.env.ref('stock.stock_location_locations_virtual', raise_if_not_found=False)
        for company in self:
            scrap_location = self.env['stock.location'].create({
                'name': 'Scrap',
                'usage': 'inventory',
                'location_id': parent_location.id,
                'company_id': company.id,
                'scrap_location': True,
            })

    def _create_scrap_sequence(self):
        scrap_vals = []
        for company in self:
            scrap_vals.append({
                'name': '%s Sequence scrap' % company.name,
                'code': 'stock.scrap',
                'company_id': company.id,
                'prefix': 'SP/',
                'padding': 5,
                'number_next': 1,
                'number_increment': 1
            })
        if scrap_vals:
            self.env['ir.sequence'].create(scrap_vals)

    @api.model
    def create_missing_warehouse(self):
        """ This hook is used to add a warehouse on the first company of the database
        """
        existing_warehouses = self.env['stock.warehouse'].search([])
        if len(existing_warehouses) == 0:
            first_company = self.env['res.company'].search([], limit=1)
            self.env['stock.warehouse'].create({
                'name': first_company.name,
                'code': first_company.name[:5],
                'company_id': first_company.id,
                'partner_id': first_company.partner_id.id,
            })

    @api.model
    def create_missing_transit_location(self):
        company_without_transit = self.env['res.company'].search([('internal_transit_location_id', '=', False)])
        company_without_transit._create_transit_location()

    @api.model
    def create_missing_inventory_loss_location(self):
        company_ids  = self.env['res.company'].search([])
        inventory_loss_product_template_field = self.env['ir.model.fields']._get('product.template', 'property_stock_inventory')
        companies_having_property = self.env['ir.default'].sudo().search([('field_id', '=', inventory_loss_product_template_field.id)]).mapped('company_id')
        company_without_property = company_ids - companies_having_property
        company_without_property._create_inventory_loss_location()

    @api.model
    def create_missing_production_location(self):
        company_ids  = self.env['res.company'].search([])
        production_product_template_field = self.env['ir.model.fields']._get('product.template', 'property_stock_production')
        companies_having_property = self.env['ir.default'].sudo().search([('field_id', '=', production_product_template_field.id)]).mapped('company_id')
        company_without_property = company_ids - companies_having_property
        company_without_property._create_production_location()

    @api.model
    def create_missing_scrap_location(self):
        company_ids  = self.env['res.company'].search([])
        companies_having_scrap_loc = self.env['stock.location'].search([('scrap_location', '=', True)]).mapped('company_id')
        company_without_property = company_ids - companies_having_scrap_loc
        company_without_property._create_scrap_location()

    @api.model
    def create_missing_scrap_sequence(self):
        company_ids  = self.env['res.company'].search([])
        company_has_scrap_seq = self.env['ir.sequence'].search([('code', '=', 'stock.scrap')]).mapped('company_id')
        company_todo_sequence = company_ids - company_has_scrap_seq
        company_todo_sequence._create_scrap_sequence()

    def _create_per_company_locations(self):
        self.ensure_one()
        self._create_transit_location()
        self._create_inventory_loss_location()
        self._create_production_location()
        self._create_scrap_location()

    def _create_per_company_sequences(self):
        self.ensure_one()
        self._create_scrap_sequence()

    def _create_per_company_picking_types(self):
        self.ensure_one()

    def _create_per_company_rules(self):
        self.ensure_one()

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        # Unarchive inter-company location when multi-company is enabled.
        inter_company_location = self.env.ref('stock.stock_location_inter_company')
        if not inter_company_location.active:
            inter_company_location.sudo().write({'active': True})
        for company in companies:
            company.sudo()._create_per_company_locations()
            company.sudo()._create_per_company_sequences()
            company.sudo()._create_per_company_picking_types()
            company.sudo()._create_per_company_rules()
            company.sudo()._set_per_company_inter_company_locations(inter_company_location)
        test_mode = getattr(threading.current_thread(), 'testing', False)
        if test_mode:
            self.env['stock.warehouse'].sudo().create([{'company_id': company.id} for company in companies])
        return companies

    def _set_per_company_inter_company_locations(self, inter_company_location):
        self.ensure_one()
        if not self.env.user.has_group('base.group_multi_company'):
            return
        other_companies = self.env['res.company'].search([('id', '!=', self.id)])
        other_companies.partner_id.with_company(self).write({
            'property_stock_customer': inter_company_location.id,
            'property_stock_supplier': inter_company_location.id,
        })
        for company in other_companies:
            # Still need to insert those one by one, as the env company must be different every time
            self.partner_id.with_company(company).write({
                'property_stock_customer': inter_company_location.id,
                'property_stock_supplier': inter_company_location.id,
            })
