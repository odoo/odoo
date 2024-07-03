                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            # -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date


class EstateVisit(models.Model):
    _name = 'estate.visit'
    _description = 'Estate Site Visit'
    _rec_name = "ref"

    estate_id = fields.Many2one('estate.property', string="Estate")
    ref = fields.Char("Reference")
    booking_date = fields.Date("Booking Date")
    visit_time = fields.Date("Visit Date")
    time_remaining = fields.Integer("Days for visit", compute='_compute_eta')
    expected_price = fields.Float("Expected Price", related="estate_id.expected_price")
    postcode = fields.Char("Postcode", related="estate_id.postcode")
    bedrooms = fields.Integer("Bedrooms", related="estate_id.bedrooms")
    buyer_name = fields.Char("Buyer")
    buyer_contact = fields.Integer("Contact")
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')], string="Priority")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_consultation', 'In Consultation'),
        ('deal', 'Deal Done'),
        ('sold', 'Sold')], string="Status", default="draft", required =True)

    @api.depends('visit_time')
    def _compute_eta(self):
        for rec in self:
            today = date.today()
            if rec.visit_time:
                diff = rec.visit_time - today
                rec.time_remaining = diff.days
            else:
                rec.time_remaining = 0

    @api.onchange('estate_id')
    def _onchange_estate_id(self):
        self.ref = self.estate_id.ref

    def test_button(self):
        print("Button clicked")