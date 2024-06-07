from odoo import http
from odoo.http import request
import json

class InscripcionController(http.Controller):

    @http.route('/ga/create-inscripcion-alumno',auth='public', methods=['POST'], csrf=False)
    def ga_inscripcion(self, **post):
        print(post.get['data'])