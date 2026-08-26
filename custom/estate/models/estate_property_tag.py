from odoo import models, fields ,api

class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Adding tags to the estate that the user insert in the database"
    _order = "name"
    name= fields.Char(
        required= True
    )

    color= fields.Integer()

    _sql_constraints = [
        ('Unique_tag','UNIQUE(name)','anther tag have this name, please use anther name')
    ]