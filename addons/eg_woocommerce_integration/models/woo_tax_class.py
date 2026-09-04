from odoo import fields, models


class WooTaxClass(models.Model):
    _name = 'woo.tax.class'
    _description = 'Woocommerce Tax Class'

    instance_id = fields.Many2one(comodel_name='eg.ecom.instance')
    provider = fields.Selection(related="instance_id.provider", store=True)
    woo_tax_class_id = fields.Integer(string="Woocommerce tax class ID")
    name = fields.Char(string="Name")
    slug = fields.Char(string="Slug")

    def import_woo_tax_class(self, instance_id):
        """
        In this create tax class in middle layer from woocommerce
        :param instance_id: Browseable object of instance
        :return: Nothing
        """
        woo_api = instance_id
        try:  # Changes by Akash
            wcapi = woo_api.get_wcapi_connection()
        except Exception as e:
            return {"warning": {"message": (
                "{}".format(e))}}
        tax_classes_response = wcapi.get('taxes/classes')
        if tax_classes_response.status_code == 200:
            for woo_tax_class in tax_classes_response.json():
                woo_tax_class_id = self.search(  # Changes by Akash
                    [('name', '=', woo_tax_class.get("name")), ('instance_id', '=', woo_api.id),
                     ('slug', '=', woo_tax_class.get("slug"))])

                if woo_tax_class_id:
                    woo_tax_class_id.write({'name': woo_tax_class.get("name"),
                                            'slug': woo_tax_class.get('slug'), })
                else:
                    self.create([{'instance_id': woo_api.id,
                                  'name': woo_tax_class.get("name"),
                                  'slug': woo_tax_class.get("slug"), }])
        else:
            return {"warning": {"message": (
                "{}".format(tax_classes_response.text))}}
