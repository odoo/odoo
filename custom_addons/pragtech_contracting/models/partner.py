# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Res Partner'

    def _get_count(self):
        work_order = self.env['work.order']
        bill = self.env['ra.bill']
        for partner in self:
            partner.work_order_count = work_order.search_count([('partner_id', 'child_of', partner.id)])
            partner.contractor_bill_count = bill.search_count([('contractor_id', 'child_of', partner.id)])

    contractor = fields.Boolean('Is a Contractor', help='Check this box if this contact is a Contractor.')
    cst_no = fields.Char('CST No')
    vat_no = fields.Char('VAT / TIN No')
    weekly_off = fields.Char('Weekly Off')
    credit_capacity = fields.Float('Credit Capacity')
    grading = fields.Char('Grading')
    pan_no = fields.Char('PAN No')
    registration_date = fields.Date('Registration Date')
    organization_type = fields.Many2one('organization.type', 'Organization Type')
    vendor_status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended'), ('blocked', 'Blocked'), ('trail', 'Trail')], 'Vendor Status')
    vendor_type = fields.Selection([('supplier', 'Supplier'), ('contractor', 'Contractor')], 'Vendor Type')
    group_id = fields.Char('Group ID')
    inbusiness_since = fields.Char('InBusiness Since')
    turn_over = fields.Float('Annual Turn Over')
    number_of_employees = fields.Integer('Number of employees')
    remark = fields.Char('Remark')
    website = fields.Char('Website')
    primary_supplier = fields.Char('Primary Supplier')
    wct_no = fields.Char('WCT No')
    shop_act_no = fields.Char('Shop Act No')
    shop_act_expiry_date = fields.Date('Shop Act Expiry Date')
    pf_code_registration_no = fields.Char(' Pf Code Registration No ')
    esic_no = fields.Char('ESIC Number')
    lwmf_no = fields.Integer('LWMF Number')
    categ_ids = fields.One2many('product.category', 'part_id', 'Partner')
    attachment_line_ids = fields.One2many('ir.attachment', 'partner_id', 'Attachment Lines')
    service_tax_no = fields.Integer('Service tax No.')

    material_category = fields.Many2many('product.category', 'partner_prod_category_rel', 'partner_id', 'category_id')
    labour_category = fields.Many2many('labour.category', 'partner_labour_category_rel', 'partner_id', 'category_id')
    work_order_count = fields.Integer(compute='_get_count', string='# of Work Order')
    contractor_bill_count = fields.Integer(compute='_get_count', string='# of Work Order')
    contractor_status = fields.Selection([('trial', 'Trial'), ('approved', 'Approved'), ('suspended', 'Suspended'), ('black_listed', 'Black Listed')], 'Contractor Status', default='trial')
    trial_allowed = fields.Integer("Trials Allowed", default=3)
    trial_used = fields.Integer("Trials Used", compute='_get_trial')
    status_remark = fields.Text(string='Status Remark')

    @api.depends('trial_allowed')
    def _get_trial(self):
        domain = []
        count = 0
        for val in self:
            if val.contractor:
                domain.append(('partner_id', '=', val.id))
                domain.append(('state', '=', 'confirm'))
                wo_obj = self.env['work.order'].search(domain)
                for wo in wo_obj:
                    count = count + 1

                val.trial_used = count
            else:
                val.trial_used = 0


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    _description = 'Res Partner Bank'

    mesge_ids = fields.One2many('mail.messages', 'res_id', string='Massage', domain=lambda self: [('model', '=', self._name)], auto_join=True, readonly=True)

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        for vals in vals_list:
            remark = vals.copy()
            remark_string = ""
            if remark.get(u'acc_number'):
                remark['Account Number'] = remark.pop(u'acc_number')

            if remark.get(u'bank_id'):
                bank_id = remark.get(u'bank_id')
                res_bank_obj = self.env['res.bank'].browse(bank_id)
                remark['Bank'] = remark.pop(u'bank_id')
                remark['Bank'] = res_bank_obj.name

            for key, value in remark.items():
                if key != 'currency_id':
                    remark_string = remark_string + "{}: {}".format(key, value) + ','

            data = []
            msg_ids = {
                'date': datetime.now(),
                'remark': remark_string,
                'author_id': self._context.get('uid'),
                'model': 'res.partner.bank'
            }
            data.append((0, 0, msg_ids))
            vals.update({'mesge_ids': data})

            return super(ResPartnerBank, self).create(vals_list)

    def write(self, vals):
        remark_string = ""
        remark = vals.copy()
        if remark.get(u'acc_number'):
            remark['Account Number'] = remark.pop(u'acc_number')

        if remark.get(u'bank_id'):
            bank_id = remark.get(u'bank_id')
            res_bank_obj = self.env['res.bank'].browse(bank_id)
            remark['Bank'] = remark.pop(u'bank_id')
            remark['Bank'] = res_bank_obj.name

        for key, value in remark.items():
            remark_string = remark_string + "{}: {}".format(key, value) + ','

        msg_ids = {
            'date': datetime.now(),
            'remark': remark_string,
            'author_id': self._context.get('uid'),
            'model': 'res.partner.bank',
            'res_id': self.id,
        }
        self.env['mail.messages'].create(msg_ids)

        return super(ResPartnerBank, self).write(vals)


class ProductCategory(models.Model):
    _inherit = 'product.category'
    _description = 'Product Category'

    part_id = fields.Many2one('res.partner', 'Partner Id')


class Product(models.Model):
    _inherit = 'product.product'

    is_labour = fields.Boolean('Is Labour?')


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    _description = 'Ir Attachment'

    partner_id = fields.Many2one('res.partner', 'Document ID')

