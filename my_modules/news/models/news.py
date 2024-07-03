# -*- coding: utf-8 -*-

from odoo import fields, models
import requests
import json
import xmlrpc.client


class News(models.Model):
    _name = "owl.news"
    _description = "News Module"

    news = fields.Text("Title", default=None)
    description = fields.Text("Description", default=None)
    imgsrc= fields.Text("Image", default=None)
    url = fields.Text("Link")

def refresh(self):
    print("yay")