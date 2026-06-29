from odoo import models, fields ,api
from datetime import date, timedelta

from odoo.exceptions import UserError

class Library_Mangement_book (models.Model):
    _name = "library.mangement.book"
    _description = "represent the books and its properties"

    name = fields.Char(
        string="Book Name",
        required=True
    )

    descreption= fields.Char()

    auther= fields.Many2one(
        'library.mangement.auther',
        string="Auther of the book",
        required=True
    )

    quantities= fields.Char(
        string= "Number of Copies",
        required= True
    )

    borrows = fields.One2many(
        'library.mangement.borrow',
        'book_id',
        ondelete="cascade"
    )

