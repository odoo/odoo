import logging
from odoo import http


_logger = logging.getLogger(__name__)


class Website1(http.Controller):
    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        data = {
            "Invoicing": "",
            "pos": "",
            "Inventory": "",
            "Settings": "",
            "Sales": "",
            "Users": ""

        }
        results = http.request.env['ir.ui.menu'].search([('name', "in", ["Invoicing", "Point of Sale", "Inventory",
                                                                         "Settings", "Sales", "Users"])])
        for i in results:
            data.update(
                {i.name: f"/web#action={i.id}" if i.action is not None else f"/web#menu_id={i.id}"} if "Point of Sale" not in i.name else {"pos": f"/web#action={i.id}" if i.action is not None else f"/web#menu_id={i.id}"})

        html_file = http.request.render('aumet.homepage_block', data)

        return html_file
