# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2022 Quartile
# Copyright 2016-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3 - See https://www.gnu.org/licenses/agpl-3.0.html

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCommissionBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.commission_model = cls.env["commission"]
        cls.commission_net_paid = cls.commission_model.create(
            {
                "name": "20% fixed commission (Net amount) - Payment Based",
                "fix_qty": 20.0,
                "amount_base_type": "net_amount",
            }
        )
        cls.commission_section_paid = cls.commission_model.create(
            {
                "name": "Section commission - Payment Based",
                "commission_type": "section",
                "section_ids": [
                    (0, 0, {"amount_from": 1.0, "amount_to": 100.0, "percent": 10.0})
                ],
                "amount_base_type": "net_amount",
            }
        )
        cls.commission_section_invoice = cls.commission_model.create(
            {
                "name": "Section commission - Invoice Based",
                "commission_type": "section",
                "section_ids": [
                    (
                        0,
                        0,
                        {
                            "amount_from": 15000.0,
                            "amount_to": 16000.0,
                            "percent": 20.0,
                        },
                    )
                ],
            }
        )
        cls.company = cls.env.ref("base.main_company")
        cls.foreign_currency = cls.env["res.currency"].create(
            {
                "name": "Coin X",
                "rounding": 0.01,
                "symbol": "CX",
            }
        )
        cls.rate = cls.env["res.currency.rate"].create(
            {
                "company_id": cls.company.id,
                "currency_id": cls.foreign_currency.id,
                "name": "2023-01-01",
                "rate": 25,
            }
        )
        cls.res_partner_model = cls.env["res.partner"]
        cls.partner = cls.env.ref("base.res_partner_2")
        cls.partner.write({"agent": False})
        cls.settle_model = cls.env["commission.settlement"]
        cls.make_settle_model = cls.env["commission.make.settle"]
        cls.commission_product = cls.env["product.product"].create(
            {"name": "Commission test product", "type": "service"}
        )
        cls.agent_monthly = cls.res_partner_model.create(
            {
                "name": "Test Agent - Monthly",
                "agent": True,
                "settlement": "monthly",
                "lang": "en_US",
                "commission_id": cls.commission_net_paid.id,
            }
        )
        cls.agent_quaterly = cls.res_partner_model.create(
            {
                "name": "Test Agent - Quaterly",
                "agent": True,
                "settlement": "quaterly",
                "lang": "en_US",
                "commission_id": cls.commission_section_invoice.id,
            }
        )
        cls.agent_semi = cls.res_partner_model.create(
            {
                "name": "Test Agent - Semi-annual",
                "agent": True,
                "settlement": "semi",
                "lang": "en_US",
            }
        )
        cls.agent_annual = cls.res_partner_model.create(
            {
                "name": "Test Agent - Annual",
                "agent": True,
                "settlement": "annual",
                "lang": "en_US",
            }
        )
        cls.agent_pending = cls.res_partner_model.create(
            {
                "name": "Test Agent - Pending",
                "agent": True,
                "settlement": "pending",
                "lang": "en_US",
            }
        )

    # Expected to be used in inheriting modules.
    def _get_make_settle_vals(self, agent=None, period=None, date=None):
        vals = {
            "date_to": (
                fields.Datetime.from_string(fields.Datetime.now())
                + relativedelta(months=period)
            )
            if period
            else date,
        }
        if agent:
            vals["agent_ids"] = [(4, agent.id)]
        return vals

    # Expected to be used in inheriting modules.
    def _check_propagation(self, agent, commission_type, agent_partner):
        self.assertTrue(agent)
        self.assertTrue(agent.commission_id, commission_type)
        self.assertTrue(agent.agent_id, agent_partner)

    def _create_settlement(self, agent, commission):
        sett_from = self.make_settle_model._get_period_start(agent, fields.Date.today())
        sett_to = self.make_settle_model._get_next_period_date(agent, sett_from)
        return self.settle_model.create(
            {
                "agent_id": agent.id,
                "date_from": sett_from,
                "date_to": sett_to,
                "company_id": self.company.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "date": fields.Date.today(),
                            "agent_id": agent.id,
                            "commission_id": commission.id,
                            "settled_amount": 100.0,
                            "currency_id": self.company.currency_id.id,
                        },
                    )
                ],
            }
        )


class TestCommission(TestCommissionBase):
    def test_wrong_section(self):
        with self.assertRaises(ValidationError):
            self.commission_model.create(
                {
                    "name": "Section commission - Invoice Based",
                    "commission_type": "section",
                    "section_ids": [
                        (0, 0, {"amount_from": 5, "amount_to": 1, "percent": 20.0})
                    ],
                }
            )

    def test_res_partner_agent_propagation(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Test partner",
                "agent_ids": [(4, self.agent_monthly.id), (4, self.agent_quaterly.id)],
            }
        )
        # Create
        child = self.env["res.partner"].create(
            {"name": "Test child", "parent_id": partner.id}
        )
        self.assertEqual(set(child.agent_ids.ids), set(partner.agent_ids.ids))
        # Write
        partner.agent_ids = [(4, self.agent_annual.id)]
        self.assertEqual(set(child.agent_ids.ids), set(partner.agent_ids.ids))

    def test_auto_subscribe_agent(self):
        settlement = self._create_settlement(
            self.agent_monthly, self.commission_net_paid
        )
        # Agent must be in the followers
        self.assertIn(self.agent_monthly, settlement.message_partner_ids)
