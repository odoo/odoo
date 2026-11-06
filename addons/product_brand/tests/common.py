# Copyright 2018 Daniel Campos <danielcampos@avanzosc.es> - Avanzosc S.L.
# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


class CommonCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.product = cls.env.ref("product.product_product_4")
        cls.supplier = cls.env.ref("base.res_partner_2")
        cls.product_brand_obj = cls.env["product.brand"]
        cls.product_brand = cls.product_brand_obj.create(
            {
                "name": "Test Brand",
                "description": "Test brand description",
                "partner_id": cls.supplier.id,
            }
        )
