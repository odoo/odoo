# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, new_test_user


class TestImLivechatCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.password = 'Pl1bhD@2!kXZ'
        cls.operators = cls.env['res.users'].create([{
            'name': 'Michel',
            'login': 'michel',
            'password': cls.password,
            'livechat_username': "Michel Operator",
            'email': 'michel@example.com',
        }, {
            'name': 'Paul',
            'login': 'paul'
        }, {
            'name': 'Pierre',
            'login': 'pierre'
        }, {
            'name': 'Jean',
            'login': 'jean'
        }, {
            'name': 'Georges',
            'login': 'georges'
        }])

        cls.visitor_user = cls.env['res.users'].create({
            'name': 'Rajesh',
            'login': 'rajesh',
            'country_id': cls.env.ref('base.in').id,
            'email': 'rajesh@example.com',
        })

        cls.livechat_channel = cls.env['im_livechat.channel'].create({
            'name': 'The channel',
            'user_ids': [(6, 0, cls.operators.ids)]
        })

    def setUp(self):
        super().setUp()

        def _compute_available_operator_ids(channel_self):
            for record in channel_self:
                record.available_operator_ids = record.user_ids

        self.patch(type(self.env['im_livechat.channel']), '_compute_available_operator_ids', _compute_available_operator_ids)


class TestGetOperatorCommon(HttpCase):
    def setUp(self):
        super().setUp()
        self.operator_id = 0

    def _create_operator(self, lang_code=None, country_code=None, expertises=None):
        self.env["res.lang"].with_context(active_test=False).search(
            [("code", "=", lang_code)]
        ).sudo().active = True
        operator = new_test_user(
            self.env(su=True), login=f"operator_{lang_code or country_code}_{self.operator_id}"
        )
        operator.res_users_settings_id.livechat_expertise_ids = expertises
        operator.partner_id = self.env["res.partner"].create(
            {
                "name": f"Operator {lang_code or country_code}",
                "lang": lang_code,
                "country_id": self.env["res.country"].search([("code", "=", country_code)]).id
                if country_code
                else None,
            }
        )
        self.env["bus.presence"].create({"user_id": operator.id, "status": "online"})  # Simulate online status
        self.operator_id += 1
        return operator
