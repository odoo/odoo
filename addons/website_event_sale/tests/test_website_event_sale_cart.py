from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.tests.common import TransactionCase, tagged, users

@tagged('post_install', '-at_install')
class WebsiteEventSaleCart(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = datetime(2039, 4, 29, 8, 0)
        cls.website = cls.env['website'].get_current_website()
        cls.WebsiteSaleController = WebsiteSale()

        cls.public_user = mail_new_test_user(
            cls.env,
            name='Public user',
            login='public_user_website_event_sale_cart',
            email='public_user@example.com',
            groups='base.group_public',
        )
        cls.product = cls.env['product.product'].create({
            'detailed_type': 'event',
            'invoice_policy': 'order',
            'name': 'Event Registration',
            'website_published': True,
        })

        cls.ongoing_stage = cls.env['event.stage'].create({
            "name": "Ongoing",
            "description": "Ongoing",
            "sequence": 0,
            "pipe_end": False,
        })
        cls.end_stage = cls.env['event.stage'].create({
            "name": "Ended",
            "description": "Fully ended",
            "sequence": 1,
            "pipe_end": True,
        })

        cls.ended_event = cls.env['event.event'].create({
            "name": "Business workshops",
            "date_begin": cls.today.replace(hour=18) - timedelta(days=5),
            "date_end": cls.today.replace(hour=22) - timedelta(days=5),
            "stage_id": cls.end_stage.id,
            "kanban_state": "done",
        })
        cls.env['event.event.ticket'].create({
            "name": "General Admission",
            "event_id": cls.ended_event.id,
            "end_sale_datetime": cls.today - timedelta(days=30),
            "product_id": cls.product.id,
        })

        cls.ongoing_event = cls.env['event.event'].create({
            "name": "OpenWood Collection Online Reveal",
            "stage_id": cls.ongoing_stage.id,
            "auto_confirm": True,
            "date_begin": cls.today.replace(hour=5) - timedelta(days=1),
            "date_end": cls.today.replace(hour=15) + timedelta(days=1)
        })
        cls.env['event.event.ticket'].create({
            "name": "Standard",
            "event_id": cls.ongoing_event.id,
            "end_sale_datetime": cls.today.replace(hour=15) + timedelta(days=2),
            "product_id": cls.product.id,
        })

        cls.planned_event = cls.env['event.event'].create({
            "name": "Conference for Architects",
            "stage_id": cls.ongoing_stage.id,
            "auto_confirm": True,
            "date_begin": cls.today.replace(hour=5) + timedelta(days=1),
            "date_end": cls.today.replace(hour=15) + timedelta(days=2)
        })
        cls.env['event.event.ticket'].create({
            "name": "Standard",
            "event_id": cls.planned_event.id,
            "end_sale_datetime": cls.today.replace(hour=15) + timedelta(days=2),
            "product_id": cls.product.id,
        })

    @users('public_user_website_event_sale_cart')
    def test_event_product_add_to_cart(self):
        with freeze_time(self.today), MockRequest(self.env, website=self.website.with_user(self.env.user)):
            self.WebsiteSaleController.cart_update_json(product_id=self.product.id, add_qty=1)
            line = self.website.sale_get_order().order_line
            self.assertEqual(line.event_id, self.planned_event)
