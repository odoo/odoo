
from odoo.tests import TransactionCase, tagged, HttpCase

@tagged('document_layout')
class TestBaseDocumentLayout(TransactionCase):

    # def setUp(self):
    #     super(TestBaseDocumentLayout, self).setUp()

    def test_default_color_flag(self):
        """ use_default_colors should be false when both primary_color and secondary_color are set """

        #FIXME wizard require a company

        # wizard = self.env['base.document.layout'].create({})
        # self.assertTrue(wizard.use_default_colors, "when no colors are set, use_default_colors should default to true")

        # wizard = self.env['base.document.layout'].create({
        #     'primary_color':'#000000',
        #     'secondary_color':'#000000',
        # })
        # self.assertFalse(wizard.use_default_colors, "when both colors are set, use_default_colors should default to false")

        pass

@tagged('document_layout_ui')
class TestBaseDocumentLayoutUI(HttpCase):
    def test_tour(self):
        """ base document layout wizard tour """
        #TODO implementation
        pass
        # self.start_tour("URL", "test_base_document_layout", login="USER_TYPE")
