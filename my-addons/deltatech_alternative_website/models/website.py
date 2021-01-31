# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import models
from odoo.http import request


class Website(models.Model):
    _inherit = "website"

    def sale_product_domain(self):
        domain = super(Website, self).sale_product_domain()
        search = request.params.get("search", False)
        if search:
            product_ids = []
            alt_domain = [("name", "ilike", search)]
            # alt_domain = []
            # for srch in search.split(" "):
            #     alt_domain += [('name', 'ilike', srch)]

            alternative_ids = self.env["product.alternative"].search(alt_domain, limit=10)
            for alternative in alternative_ids:
                product_ids += [alternative.product_tmpl_id.id]
            if product_ids:
                if len(product_ids) == 1:
                    domain += ["|", ("id", "=", product_ids[0])]
                else:
                    domain += ["|", ("id", "in", product_ids)]

        return domain
