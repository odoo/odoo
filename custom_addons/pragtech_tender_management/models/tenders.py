# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.http_routing.models.ir_http import slug


class TendersTenders(models.Model):
    _name = 'tenders.tenders'
    _inherit = ["website.seo.metadata", 'website.published.multi.mixin']
    _description = 'Tenders'

    name = fields.Char('Name', default="/")
    tender_name = fields.Char('Tender Name')
    comment = fields.Char(compute='_compute_comment')
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    zip = fields.Char('Zip')
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    user_id = fields.Many2one('res.partner', 'Responsible')
    start_date = fields.Datetime("Bid from", default=fields.Datetime.now)
    end_date = fields.Datetime("Bid to")  # no start and end = always active
    top_rank = fields.Char('Top rank')
    tender_line_id = fields.One2many('tenders.tenders.line', 'line_id')
    tender_overhead_id = fields.One2many('tenders.overhead', 'overhead_id')
    tender_labour_id = fields.One2many('tenders.labour', 'labour_id')
    tender_question_ids = fields.One2many('question.question', 'question_id', 'Tender Questions')
    department = fields.Many2one('res.department', string='Department', help='Name of the department inviting tender')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approve', 'Approve'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], string='Status', readonly=True, copy=False, index=True, default='draft')
    website_published = fields.Boolean(default=True)
    bids_id = fields.Many2one('bids.bids')
    count_bids = fields.Integer(compute='_compute_bids_id')
    all_total = fields.Float(default=0.0)
    total_budget = fields.Float(string='Total Budget')
    earnest_money_deposit = fields.Float(string='Earnest Money Deposit')
    performance_security_deposit = fields.Float(string='Performance Security Deposit')
    liquidated_damage = fields.Float(string='Liquidated Damage')
    unliquidated_damage = fields.Float(string='Un-Liquidated Damage')
    pre_bid_meeting_date = fields.Datetime("Pre-bid Meeting Date")
    pre_bid_meeting_mom = fields.Html('Pre-bid Meeting MOM')
    documents_ids = fields.One2many('ir.attachment', 'tender_id', 'Documents')
    enquiries_ids = fields.One2many('tender.enquiries', 'tender_id', 'Enquiries')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tenders.tenders.seq') or '/'

        return super(TendersTenders, self).create(vals_list)

    def action_view_bids(self):
        tree_view_id = self.env.ref('pragtech_tender_management.bids_tree_view').id
        form_view_id = self.env.ref('pragtech_tender_management.bids_form_view').id
        bids = []
        if self.tender_name:
            bids.append(self.tender_name)
            return {
                'name': self.name,
                'res_model': 'bids.bids',
                'type': 'ir.actions.act_window',
                'view_mode': 'tree',
                'view_id': tree_view_id,
                'domain': [('tender_id', '=', bids)],
                'views': [
                    (tree_view_id, 'tree'),
                    (form_view_id, 'form'),
                ],
                'res_id': False,
                'context': False,
            }

    @api.depends('bids_id')
    def _compute_bids_id(self):
        for bids in self:
            bids_ids = bids.env['bids.bids'].search([('tender_id', 'in', bids.tender_name)])
            bids.count_bids = len(bids_ids)

    def action_tender_submit(self):
        self.write({
            'state': 'submitted'
        })

    def action_tender_approve(self):
        self.write({
            'state': 'approve'
        })

    def action_tender_cancel(self):
        self.write({
            'state': 'rejected'
        })

    def _compute_website_url(self):
        super(TendersTenders, self)._compute_website_url()
        for tenders in self:
            tenders.website_url = "/tenders/view/%s" % slug(tenders)


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    tender_id = fields.Many2one('tenders.tenders', 'Tenders')


class TendersTendersLine(models.Model):
    _name = 'tenders.tenders.line'
    _description = 'Tenders Line'

    line_id = fields.Many2one('tenders.tenders')
    product_id = fields.Many2one('product.product')
    line_description = fields.Text(string='Description')
    product_uom_qty = fields.Float('Quantity', default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Product UoM')
    material_last_price = fields.Float('Last price')
    material_your_price = fields.Float()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_uom_qty') < 1.0:
                raise UserError('Material quantity should be greater than or equal to 1.')

            if not vals.get('product_uom'):
                raise UserError('Please select material units.')

        return super(TendersTendersLine, self).create(vals_list)

    def write(self, vals):
        result = super(TendersTendersLine, self).write(vals)
        for rec in self:
            if rec.product_uom_qty < 1.0:
                raise UserError('Material quantity should be greater than or equal to 1.')

            if not rec.product_uom:
                raise UserError('Please select material units.')

        return result

    @api.onchange('product_id')
    def product_id_change(self):
        if self.product_id:
            self.line_description = self.product_id.name


class TendersLabour(models.Model):
    _name = 'tenders.labour'
    _description = 'Tenders Labour'

    labour_id = fields.Many2one('tenders.tenders')
    tender_labour_labour_id = fields.Many2one('labours.labour', 'Name')
    labour_description = fields.Text(string='Description')
    labour_qty = fields.Float('Quantity', default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Labour UoM')
    labour_last_price = fields.Float('Last price')
    labour_your_price = fields.Float()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('labour_qty') < 1.0:
                raise UserError('Labour quantity should be greater than or equal to 1.')

            if not vals.get('product_uom'):
                raise UserError('Please select labour units.')

        return super(TendersLabour, self).create(vals_list)

    def write(self, vals):
        result = super(TendersLabour, self).write(vals)
        for rec in self:
            if rec.labour_qty < 1.0:
                raise UserError('Labour quantity should be greater than or equal to 1.')

            if not rec.product_uom:
                raise UserError('Please select labour units.')

        return result

    @api.onchange('tender_labour_labour_id')
    def labour_details(self):
        if self.tender_labour_labour_id:
            self.labour_description = self.tender_labour_labour_id.labour_description


class LaboursLabours(models.Model):
    _name = 'labours.labour'
    _description = 'Labours Labours'

    name = fields.Char()
    labour_description = fields.Text(string='Description')
    labour_qty = fields.Float('Quantity')
    product_uom = fields.Many2one('uom.uom', string='Labour UoM')
    labour_last_price = fields.Float('Last price')


class OverheadOverhead(models.Model):
    _name = 'overhead.overhead'
    _description = 'Overhead Overhead'

    name = fields.Char()
    overhead_description = fields.Text(string='Description')
    overhead_qty = fields.Float('Quantity')
    product_uom = fields.Many2one('uom.uom', string='Overhead UoM')
    overhead_last_price = fields.Float('Last price')


class TendersOverheads(models.Model):
    _name = 'tenders.overhead'
    _description = 'Tenders Overhead'

    overhead_id = fields.Many2one('tenders.tenders')
    tender_overhead_overhead_id = fields.Many2one('overhead.overhead', 'Name')
    overhead_description = fields.Text(string='Description')
    overhead_qty = fields.Float('Quantity', default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Overhead UoM')
    overhead_last_price = fields.Float('Last price')
    overhead_your_price = fields.Float()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('overhead_qty') < 1.0:
                raise UserError('Overhead quantity should be greater than or equal to 1.')

            if not vals.get('product_uom'):
                raise UserError('Please select overhead units.')

        return super(TendersOverheads, self).create(vals_list)

    def write(self, vals):
        result = super(TendersOverheads, self).write(vals)
        for rec in self:
            if rec.overhead_qty < 1.0:
                raise UserError('Overhead quantity should be greater than or equal to 1.')

            if not rec.product_uom:
                raise UserError('Please select overhead units.')

        return result

    @api.onchange('tender_overhead_overhead_id')
    def overhead_details(self):
        if self.tender_overhead_overhead_id:
            self.overhead_description = self.tender_overhead_overhead_id.overhead_description


class ResDepartment(models.Model):
    _name = "res.department"
    _description = "Department master"
    name = fields.Char(string="Name", required=True, help="Name of the department")


class TenderQuestions(models.Model):
    _name = "tender.questions"
    _description = "Tender Questions"

    name = fields.Char(string='Text', required=True)
    type = fields.Selection([('text', 'Text'), ('number', 'Numerical')])


class Question(models.Model):
    _name = 'question.question'
    _description = 'Rating Questionnaire'

    question_id = fields.Many2one('tenders.tenders')
    tender_question_id = fields.Many2one('tender.questions', 'Name')
    type = fields.Selection([('text', 'Text'), ('number', 'Numerical')])

    @api.onchange('tender_question_id')
    def questionnaire_details(self):
        if self.tender_question_id:
            self.type = self.tender_question_id.type


class JobType(models.Model):
    _name = 'job.type'
    _description = 'Job Type'

    name = fields.Char('Name')


class TenderEnquiries(models.Model):
    _name = 'tender.enquiries'
    _description = 'Tender Enquiries'

    tender_id = fields.Many2one('tenders.tenders', copy=False)
    name = fields.Char('Name', default="/", copy=False)
    contractor_id = fields.Many2one('res.partner', 'Contractor')
    job_type = fields.Many2one('job.type', 'Job Type')
    date = fields.Date('Date')
    submission_date = fields.Date('Submission Date')
    state = fields.Selection([('draft', 'Draft'), ('approve', 'Approved')], default='draft')
    tender_enquiry_ids = fields.One2many('tenders.questions', 'enquiry_id')
    total_score = fields.Float(compute="_compute_total_score", string='Total Score')

    @api.onchange('tender_id')
    def onchange_tender_id(self):
        question_list = []
        if self.tender_id:
            for tender_question_id in self.tender_id.tender_question_ids:
                question_list.append((0, 0, {
                    'question_id': tender_question_id.tender_question_id.id,
                }))

            self.tender_enquiry_ids = question_list
        else:
            self.tender_enquiry_ids = [(6, 0, [])]

    @api.depends('tender_enquiry_ids', 'tender_enquiry_ids.score', 'tender_id')
    def _compute_total_score(self):
        for rec in self:
            rec.total_score = sum([i.score for i in rec.tender_enquiry_ids])

    def action_approve(self):
        self.state = 'approve'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tenders.enquiries.seq') or '/'

        return super(TenderEnquiries, self).create(vals_list)


class TendersQuestions(models.Model):
    _name = 'tenders.questions'
    _description = 'Tenders Questions'

    enquiry_id = fields.Many2one('tender.enquiries', 'Enquiry')
    question_id = fields.Many2one('tender.questions', 'Question')
    score = fields.Integer('Score')


class TenderEstimation(models.Model):
    _name = 'tender.estimation'
    _description = 'Tender Estimation'

    name = fields.Char('Name', default="/", copy=False)
    enquiry_id = fields.Many2one('tender.enquiries', 'Enquiry')
    tender_id = fields.Many2one(related="enquiry_id.tender_id")
    contractor_id = fields.Many2one(related="enquiry_id.contractor_id")
    reviewer_id = fields.Many2one('res.users', 'Reviewer')
    submission_date = fields.Date(related="enquiry_id.submission_date")
    tenders_estimation_material_ids = fields.One2many('tenders.estimation.material', 'estimation_id')
    tenders_estimation_labour_ids = fields.One2many('tenders.estimation.labour', 'estimation_id')
    total_estimation = fields.Float(compute="_compute_total_estimation", string='Total Estimation')

    @api.depends('tenders_estimation_material_ids', 'tenders_estimation_material_ids.total_rate', 'tenders_estimation_labour_ids', 'tenders_estimation_labour_ids.total_rate')
    def _compute_total_estimation(self):
        for rec in self:
            material_rate = sum([i.total_rate for i in rec.tenders_estimation_material_ids])
            labour_rate = sum([i.total_rate for i in rec.tenders_estimation_labour_ids])
            rec.total_estimation = material_rate + labour_rate

    def action_approve(self):
        self.state = 'approve'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('tenders.estimation.seq') or '/'

            return super(TenderEstimation, self).create(vals_list)


class TendersEstimationMaterial(models.Model):
    _name = 'tenders.estimation.material'
    _description = 'TendersEstimationMaterial'

    product_id = fields.Many2one('product.product', 'Cost Code')
    name = fields.Char(related="product_id.name", readonly=False)
    bom = fields.Char('BOM')
    remarks = fields.Char('Remarks')
    qty = fields.Float('Qty', default=1.0)
    product_uom = fields.Many2one(related="product_id.uom_id", readonly=False, string='Unit')
    rate = fields.Float(related="product_id.lst_price", string='Rate', readonly=False)
    total_rate = fields.Float(compute='_compute_total_rate', string="Total")
    estimation_id = fields.Many2one('tender.estimation', 'Estimation')

    @api.depends('qty', 'rate', 'product_id')
    def _compute_total_rate(self):
        for rec in self:
            rec.total_rate = rec.qty * rec.rate


class TendersEstimationLabour(models.Model):
    _name = 'tenders.estimation.labour'
    _description = 'Tenders Estimation Labour'

    product_id = fields.Many2one('product.product', 'Cost Code')
    name = fields.Char(related="product_id.name", readonly=False)
    time_sheet_product = fields.Char('Time Sheet Product')
    remarks = fields.Char('Remarks')
    qty = fields.Float('Qty', default=1.0)
    product_uom = fields.Many2one(related="product_id.uom_id", readonly=False, string='Unit')
    rate = fields.Float(related="product_id.lst_price", string='Rate', readonly=False)
    total_rate = fields.Float(compute='_compute_total_rate', string="Total")
    estimation_id = fields.Many2one('tender.estimation', 'Estimation')

    @api.depends('qty', 'rate', 'product_id')
    def _compute_total_rate(self):
        for rec in self:
            rec.total_rate = rec.qty * rec.rate

