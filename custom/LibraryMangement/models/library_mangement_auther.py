from odoo import models, fields ,api

class library_mangement_auther(models.Model):
    _name = "library.mangement.auther"
    _description = "this model related to the auther of the book who write the book"

    name= fields.Char(
        string="Name of the Auther"
    )

    descreption= fields.Char()

    age= fields.Integer(
        default=18
    )

    books =fields.One2many(
        'library.mangement.book',
        'auther',
        string='Auther of these books',
        required=True
    )



    #_sql_constraints = []