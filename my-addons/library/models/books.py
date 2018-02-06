# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _

class Books(models.Model):
    _inherit = 'product.product'

    author_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Authors",
        domain=[('author','=',True), ],
    )
    edition_date = fields.Date(string='Edition date',)
    isbn = fields.Char(string='ISBN')
    publisher_id = fields.Many2one(
        'res.partner',
        string='Publisher',
        domain=[('publisher','=',True), ],
    )
    rental_ids = fields.One2many(
        'library.rental',
        'book_id',
        string='Rentals',)
    book = fields.Boolean('is a book', default=False)
