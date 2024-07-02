# -*- coding: utf-8 -*-

from odoo import fields, models
import requests
import json
import xmlrpc.client


class News(models.Model):
    _name = "owl.news"
    _description = "News Module"

    news = fields.Text("Title", allow_none=True)
    description = fields.Text("Description", allow_none=True)
    imgsrc= fields.Text("Image", allow_none=True)
    url = fields.Text("Link")

def refresh(self):
    print("yay")