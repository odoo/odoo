from odoo.tests import TransactionCase, tagged, Form


@tagged('-at_install', 'post_install')
class TestFormCreate(TransactionCase):
    """
    Test that the basic Odoo models records can be created on
    the interface.
    """

    def test_create_res_partner_bank(self):
        bank_account_form = Form(self.env['res.partner.bank'].with_context(default_partner_id=self.env.user.partner_id.id))
        bank_account_form.account_number = '11234'
        bank_account_form.save()
