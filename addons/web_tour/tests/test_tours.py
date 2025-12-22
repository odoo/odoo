from odoo.tests import tagged
from odoo import Command
from odoo.addons.base.tests.common import BaseCommon
from markupsafe import Markup


@tagged('post_install', '-at_install')
class TestTour(BaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tour_1 = cls.env["web_tour.tour"].create({
            "name": "my_tour",
            "url": "my_url",
            "sequence": 2,
            "step_ids": [Command.create(
                {
                    "content": "Click here",
                    "trigger": "button",
                    "run": "click",
                }),
            ]
        })

        cls.tour_2 = cls.env["web_tour.tour"].create({
            "name": "your_tour",
            "url": "my_url",
            "custom": True,
            "sequence": 3,
            "step_ids": [Command.create({
                    "content": "Click here",
                    "trigger": "button",
                    "run": "click",
                }),
                Command.create({
                    "content": "Edit here",
                    "trigger": "input",
                    "run": "edit 5",
                }),
            ]
        })

        cls.tour_3 = cls.env["web_tour.tour"].create({
            "name": "their_tour",
            "url": "my_url",
            "sequence": 1,
        })

    def test_get_tour_json_by_name(self):
        tour = self.env["web_tour.tour"].get_tour_json_by_name("my_tour")

        self.assertEqual(tour, {
            "name": "my_tour",
            "url": "my_url",
            "custom": False,
            "rainbowManMessage": Markup("<span><b>Good job!</b> You went through all steps of this tour.</span>"),
            "steps": [{
                "content": "Click here",
                "trigger": "button",
                "run": "click",
            }]
        })

    def test_get_current_tour(self):
        self.env.user.tour_enabled = True
        tour = self.env["web_tour.tour"].get_current_tour()
        self.assertEqual(tour["name"], "their_tour")
        self.env["web_tour.tour"].consume("their_tour")
        tour = self.env["web_tour.tour"].get_current_tour()
        self.assertEqual(tour["name"], "my_tour")
        self.env["web_tour.tour"].consume("my_tour")
        self.env.user.tour_enabled = False
        tour = self.env["web_tour.tour"].get_current_tour()
        self.assertEqual(bool(tour), False)
