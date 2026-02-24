# -*- coding: utf-8 -*-

from odoo import fields, models


class BidsBids(models.Model):
    _name = 'bids.bids'
    _rec_name = 'bids_name'
    _order = "bids_top_rank"
    _description = 'Bids Bids'

    bids_name = fields.Char('Name')
    bids_comment = fields.Char(compute='_compute_comment')
    bids_street = fields.Char('Street')
    bids_street2 = fields.Char('Street2')
    bids_zip = fields.Char('Zip')
    bids_city = fields.Char('City')
    bids_state_id = fields.Many2one("res.country.state", string='State')
    bids_country_id = fields.Many2one('res.country', string='Country')
    bids_user_id = fields.Many2one('res.partner', 'Responsible')
    bids_top_rank = fields.Integer('Ranking')
    bids_start_date = fields.Datetime("Start Date", default=fields.Datetime.now)
    bids_end_date = fields.Datetime("End Date")  # no start and end = always active
    bids_line_id = fields.One2many('bids.bids.line', 'line_id')
    bids_labour_id = fields.One2many('bids.labour', 'bids_labour_id')
    bids_overhead_id = fields.One2many('bids.overhead', 'bids_overhead_id')
    bids_question_ids = fields.One2many('bids.questions', 'bids_id', 'Bids Questions')
    state = fields.Selection([
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ], string='Status', readonly=True, copy=False, index=True, default='submitted')
    bids_all_total = fields.Float('Total')
    name_of_bidder = fields.Many2one('res.users', 'Name of bidders')
    tender_id = fields.Many2one('tenders.tenders', 'Tender name')

    def action_bids_under_review(self):
        self.write({
            'state': 'under_review'
        })

        bids_of_my_tender_status = self.env['tenders.tenders'].search([('id', '=', self.tender_id.id)])
        for tender_status in bids_of_my_tender_status:
            tender_status.state = 'in_progress'

    def action_bids_won(self):
        bids_of_my_tender = self.env['bids.bids'].search([('tender_id', '=', self.tender_id.id)])
        for bids in bids_of_my_tender:
            if bids.id == self.id:
                bids.write({
                    'state': 'won'
                })
                bids_of_my_tender_status = self.env['tenders.tenders'].search([('id', '=', self.tender_id.id)])

                for tender_status in bids_of_my_tender_status:
                    tender_status.state = 'done'

                bids.tender_id.top_rank = bids.name_of_bidder.display_name
            else:
                bids.write({
                    'state': 'lost'
                })
                bids_of_my_tender_status = self.env['tenders.tenders'].search([('id', '=', self.tender_id.id)])
                for tender_status in bids_of_my_tender_status:
                    tender_status.state = 'done'


class BidsBidsLine(models.Model):
    _name = 'bids.bids.line'
    _description = 'Bids Line'

    line_id = fields.Many2one('bids.bids')
    bids_product_id = fields.Many2one('product.product', string='Name')
    bids_description = fields.Text(string='Description')
    bids_product_uom_qty = fields.Float('Quantity')
    bids_product_uom = fields.Many2one('uom.uom', string='Product UoM')
    mat_your_price = fields.Float("Your price")
    mat_last_price = fields.Float("Last price")
    mat_note = fields.Char("Notes")
    mat_amount = fields.Float("Amount")


class BidsLabour(models.Model):
    _name = 'bids.labour'
    _description = 'Bids Labour'

    bids_labour_id = fields.Many2one('bids.bids')
    labour_id = fields.Many2one('labours.labour', string='Name')
    bids_labour_description = fields.Text(string='Description')
    bids_labour_qty = fields.Float('Quantity')
    bids_labour_product_uom = fields.Many2one('uom.uom', string='Labour UoM')
    bids_labour_your_price = fields.Float("Your price")
    bids_labour_last_price = fields.Float("Last price")
    bids_labour_note = fields.Char("Notes")
    bids_labour_amount = fields.Float("Amount")


class BidsLaboursLabours(models.Model):
    _name = 'bids.labours.labour'
    _description = 'Bids Labours Labour'

    name = fields.Char()
    bids_labour_description = fields.Text(string='Description')
    bids_labour_qty = fields.Float('Quantity')
    bids_labour_product_uom = fields.Many2one('uom.uom', string='Labour UoM')


class BidsOverheadOverhead(models.Model):
    _name = 'bids.overhead.overhead'
    _description = 'Bids Overhead Overhead'

    name = fields.Char()
    bids_overhead_description = fields.Text(string='Description')
    bids_overhead_qty = fields.Float('Quantity')
    bids_overhead_product_uom = fields.Many2one('uom.uom', string='Overhead UoM')


class TendersOverheads(models.Model):
    _name = 'bids.overhead'
    _description = 'Bids Overhead'

    bids_overhead_id = fields.Many2one('bids.bids')
    overhead_id = fields.Many2one('overhead.overhead', 'Name')
    bids_overhead_description = fields.Text(string='Description')
    bids_overhead_qty = fields.Float('Quantity')
    bids_overhead_product_uom = fields.Many2one('uom.uom', string='Overhead UoM')
    bids_overhead_last_price = fields.Float('Last price')
    bids_overhead_your_price = fields.Float("Your price")
    bids_overhead_note = fields.Char("Notes")
    bids_overhead_amount = fields.Float("Amount")


class TenderQuestions(models.Model):
    _name = "bids.questions"
    _description = 'Bids Questions'

    bids_id = fields.Many2one('bids.bids', 'Bids', required=True)
    question = fields.Char(string='Question')
    answer = fields.Char(string='Answer')

