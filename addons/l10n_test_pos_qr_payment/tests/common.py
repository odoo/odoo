from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


class TestPosQrCommon(AccountTestInvoicingHttpCommon):
    @classmethod
    def get_default_groups(cls):
        # The POS fixtures flip `available_in_pos` on the products they build,
        # and that field is gated on the sales manager group. point_of_sale
        # does not depend on sale_team, so resolve it optionally, the way
        # AccountTestInvoicingCommon resolves mrp, purchase and stock.
        no_group = cls.env["res.groups"].browse()
        return super().get_default_groups() | (
            cls.env.ref("sale.group_sale_manager", False) or no_group
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data["company"].qr_code = True

        cls.env["product.combo.item"].search([]).unlink()
        cls.env["product.product"].search([]).write({"available_in_pos": False})

        cls.product_1 = cls.env["product.product"].create(
            {
                "name": "Hand Bag",
                "available_in_pos": True,
                "list_price": 4.8,
                "taxes_id": False,
            }
        )

        # Create user.
        cls.pos_user = cls.env["res.users"].create(
            {
                "name": "A simple PoS man!",
                "login": "pos_user",
                "password": "pos_user",
                "group_ids": [
                    (4, cls.env.ref("base.group_user").id),
                    (4, cls.env.ref("point_of_sale.group_pos_user").id),
                    (4, cls.env.ref("account.group_account_invoice").id),
                ],
            }
        )

        cls.company = cls.company_data["company"]
        cls.pos_receivable_bank = cls.copy_account(
            cls.company.account_default_pos_receivable_account_id,
            {"name": "POS Receivable Bank"},
        )
        cls.outstanding_bank = cls.copy_account(
            cls.inbound_payment_channel.payment_account_id, {"name": "Outstanding Bank"}
        )
        cls.bank_pm = (
            cls.env["pos.payment.method"]
            .sudo()
            .create(
                {
                    "name": "Bank",
                    "journal_id": cls.company_data["default_journal_bank"].id,
                    "receivable_account_id": cls.pos_receivable_bank.id,
                    "outstanding_account_id": cls.outstanding_bank.id,
                    "company_id": cls.company.id,
                }
            )
        )

        cls.main_pos_config = (
            cls.env["pos.config"]
            .sudo()
            .create(
                {
                    "name": "Shop",
                    "module_pos_restaurant": False,
                    "journal_id": cls.company_data["default_journal_sale"].id,
                    # Make sure there is one extra payment method for the tour tests to work.
                    # Because if the tour only use the qr payment method, the total amount won't be displayed,
                    # causing the tour test to fail.
                    "payment_method_ids": [(4, cls.bank_pm.id)],
                }
            )
        )
