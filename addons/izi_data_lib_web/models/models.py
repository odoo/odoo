from odoo import models, fields, api, _
from odoo.exceptions import UserError
from bs4 import BeautifulSoup
import io
import requests

class IZITools(models.TransientModel):
    _inherit = 'izi.tools'

    @api.model
    def lib(self, key):
        lib = {
            'BeautifulSoup': BeautifulSoup,
            'requests': requests,
        }
        if key in lib:
            return lib[key]
        return super(IZITools, self).lib(key)
    
    @api.model
    def requests(self, method, url, headers={}, data={}):
        response = requests.request(method, url=url, headers=headers, data=data)
        return response

    @api.model
    def requests_io(self, method, url, headers={}, data={}):
        response = requests.request(method, url=url, headers=headers, data=data)
        return io.StringIO(response.content.decode('utf-8'))
    
