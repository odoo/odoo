from odoo.tests.common import TransactionCase
from lxml import etree

class TestSaleOrderView(TransactionCase):

    def test_payment_term_id_is_invisible(self):
        # Obtener la vista heredada combinada de 'sale.order' tipo 'form'
        View = self.env['ir.ui.view']
        view_id = self.env.ref('sale.view_order_form').id
        combined_view = View.browse(view_id).read_combined(['arch'])['arch']
        tree = etree.fromstring(combined_view)

        # Buscar el campo 'validity_date'
        field_node = tree.xpath("//field[@name='payment_term_id']")
        self.assertTrue(field_node, "El campo 'payment_term_id' no existe en la vista.")

        # Verificar que tenga el atributo invisible
        invisible_attr = field_node[0].get('invisible')
        self.assertTrue(invisible_attr == "1", "El campo 'payment_term_id' no está oculto correctamente.")

    def test_order_template_is_invisible(self):
        # Obtener la vista heredada combinada de 'sale.order' tipo 'form'
        View = self.env['ir.ui.view']
        view_id = self.env.ref('sale.view_order_form').id
        combined_view = View.browse(view_id).read_combined(['arch'])['arch']
        tree = etree.fromstring(combined_view)

        # Buscar el campo 'validity_date'
        field_node = tree.xpath("//field[@name='sale_order_template_id']")
        self.assertTrue(field_node, "El campo 'sale_order_template_id' no existe en la vista.")

        # Verificar que tenga el atributo invisible
        invisible_attr = field_node[0].get('invisible')
        self.assertTrue(invisible_attr == "1", "El campo 'sale_order_template_id' no está oculto correctamente.")

    def test_optional_products_is_invisible(self):
            # Obtener la vista heredada combinada de 'sale.order' tipo 'form'
            View = self.env['ir.ui.view']
            view_id = self.env.ref('sale.view_order_form').id
            combined_view = View.browse(view_id).read_combined(['arch'])['arch']
            tree = etree.fromstring(combined_view)

            # Buscar el campo 'validity_date'
            field_node = tree.xpath("//page[@name='other_information']")
            self.assertTrue(field_node, "La página 'other_information' no existe en la vista.")

            # Verificar que tenga el atributo invisible
            invisible_attr = field_node[0].get('invisible')
            self.assertTrue(invisible_attr == "1", "La página 'other_information' no está oculta correctamente.")

    def test_customer_signature_is_invisible(self):
            # Obtener la vista heredada combinada de 'sale.order' tipo 'form'
            View = self.env['ir.ui.view']
            view_id = self.env.ref('sale.view_order_form').id
            combined_view = View.browse(view_id).read_combined(['arch'])['arch']
            tree = etree.fromstring(combined_view)

            # Buscar el campo 'validity_date'
            field_node = tree.xpath("//page[@name='customer_signature']")
            self.assertTrue(field_node, "La página 'customer_signature' no existe en la vista.")

            # Verificar que tenga el atributo invisible
            invisible_attr = field_node[0].get('invisible')
            self.assertTrue(invisible_attr == "1", "La página 'customer_signature' no está oculta correctamente.")

    def test_quotation_pdf_creator_is_invisible(self):
            # Obtener la vista heredada combinada de 'sale.order' tipo 'form'
            View = self.env['ir.ui.view']
            view_id = self.env.ref('sale.view_order_form').id
            combined_view = View.browse(view_id).read_combined(['arch'])['arch']
            tree = etree.fromstring(combined_view)

            # Buscar el campo 'validity_date'
            field_node = tree.xpath("//page[@name='quotation_pdf_creator']")
            self.assertTrue(field_node, "La página 'quotation_pdf_creator' no existe en la vista.")

            # Verificar que tenga el atributo invisible
            invisible_attr = field_node[0].get('invisible')
            self.assertTrue(invisible_attr == "1", "La página 'quotation_pdf_creator' no está oculta correctamente.")