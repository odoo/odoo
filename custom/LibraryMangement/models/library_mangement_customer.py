from odoo import models, fields,api

class library_mangement_customer(models.Model):
    _name = "library.mangement.customer"
    _description = "the customer can brow and return the books to the library"


    name= fields.Char(
        required =True
    )
    age= fields.Integer(
        required=True
    )
    borrow_list= fields.One2many(
        'library.mangement.borrow',
        'customer_id',
        string="borrow History",
        required =True
    )

