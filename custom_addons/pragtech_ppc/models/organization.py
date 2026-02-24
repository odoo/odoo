# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class Brand(models.Model):
    _name = 'brand.brand'
    _description = 'Brand'

    name = fields.Char('Name', required=True)
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    material_id = fields.Many2one('product.template', 'Material')


class LbtLocationMaster(models.Model):
    _name = 'lbt.location.master'
    _description = 'Lbt Location Master'

    name = fields.Char('Name', required=True)
    description = fields.Text('Remark/Description')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')


class PaymentScheduleTemplate(models.Model):
    _name = 'payment.schedule.template'
    _description = 'Payment Schedule Template'

    name = fields.Char('Template Name', required=True)
    template_detail_line = fields.One2many('payment.schedule.template.line', 'template_id', string='Template Line')
    total = fields.Float('Total', compute='_compute_total', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            total = 0.0
            res = vals.get('template_detail_line')
            for re in res:
                total += re[2].get('installment_per')

            if total != 100:
                raise UserError('plz check installment percent should be 100.')

        return super(PaymentScheduleTemplate, self).create(vals_list)

    @api.depends('template_detail_line.installment_per')
    def _compute_total(self):
        total1 = 0.0
        for template_line in self.template_detail_line:
            total1 += template_line.installment_per
        self.total = total1


class PaymentScheduleTemplateLine(models.Model):
    _name = 'payment.schedule.template.line'
    _description = 'Payment Schedule Template Line'

    installment_desc = fields.Char('Installment Description')
    installment_per = fields.Float('Installment Percentage(%)')
    template_id = fields.Many2one('payment.schedule.template', 'Payment Schedule Template')


class OrganizationType(models.Model):
    _name = 'organization.type'
    _description = 'Organization Type'

    name = fields.Char('Organization Type')
    user_name = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    description = fields.Text('Remark/Description')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    date = fields.Date('Date', default=fields.date.today())


class StoreType(models.Model):
    _name = 'store.type'
    _description = 'Store Type'

    name = fields.Char('Name', required=True)


class RemarkMaster(models.Model):
    _name = 'remark.master'
    _description = 'Remark Master'

    name = fields.Char('Name', required=True)
    parent_id = fields.Many2one('remark.master', 'Remark')
    type = fields.Selection([('po', 'PO'), ('wo', 'WO'), ('supplier', 'Supplier'), ('contractor', 'Contractor')], 'Type')
    description = fields.Text('Remark/Description')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    user_name = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    date = fields.Date('Date', default=fields.date.today())


class ServiceTaxSchemes(models.Model):
    _name = 'service.tax.schemes'
    _description = 'Service Tax Schemes'

    name = fields.Char('Name', required=True)
    org_type_id = fields.Many2one('organization.type', 'Organization')
    ser_prov_cont = fields.Float('Service Providers Contribution')
    ser_rec_cont = fields.Float('Service Receivers Contribution')
    description = fields.Text('Remark/Description')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], 'Status')
    user_name = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    date = fields.Date('Date', default=fields.date.today())

