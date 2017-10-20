# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

# !! Attention, this is a hack of a hack, do not try this at home !!
# This is done because website_sale defines the website_description
# field which is also defined by website_quote, but these two modules
# are independent of each other, the part of the ORM that generates
# xmlids does not support this case therefore it only creates a single
# pair of xmlids for whichever module is installed first, therefore
# when uninstalling any of the two modules the website_descripion field
# will be deleted from the db and the other module won't be able to
# use this field, resulting in a crash and data-loss.
# See opw-776464 for more details.
#
# This is hotfixed by overriding the unlink method so as to not delete
# the website_description field if website_sale is uninstalled, it's
# an ugly hack but it works and big changes can't be done to the ORM
# in stable versions, Odoo v12+ will properly fix this


class IrModelFields(models.Model):
    _inherit = "ir.model.fields"

    @api.multi
    def unlink(self):
        # Prevent the deletion of the field "website_description"
        self = self.filtered(
            lambda rec: not (
                rec.model in ('product.product', 'product.template') and
                rec.name == 'website_description'
            )
        )
        return super(IrModelFields, self).unlink()
