# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase, TransactionCase, HttpCase


class TransactionCaseWithUserDemo(TransactionCase):

    def setUp(self):
        super(TransactionCaseWithUserDemo, self).setUp()

        self.env.ref('base.partner_admin').write({'name': 'Mitchell Admin'})
        self.user_demo = self.env['res.users'].search([('login', '=', 'demo')])
        self.partner_demo = self.user_demo.partner_id

        if not self.user_demo:
            self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            # YTI TODO: This could be factorized between the different classes
            self.partner_demo = self.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            self.user_demo = self.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': self.partner_demo.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('base.group_partner_manager').id])],
            })


class HttpCaseWithUserDemo(HttpCase):

    def setUp(self):
        super(HttpCaseWithUserDemo, self).setUp()
        self.user_admin = self.env.ref('base.user_admin')
        self.user_admin.write({'name': 'Mitchell Admin'})
        self.partner_admin = self.user_admin.partner_id
        self.user_demo = self.env['res.users'].search([('login', '=', 'demo')])
        self.partner_demo = self.user_demo.partner_id

        if not self.user_demo:
            self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            self.partner_demo = self.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            self.user_demo = self.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': self.partner_demo.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('base.group_partner_manager').id])],
            })


class SavepointCaseWithUserDemo(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(SavepointCaseWithUserDemo, cls).setUpClass()

        cls.user_demo = cls.env['res.users'].search([('login', '=', 'demo')])
        cls.partner_demo = cls.user_demo.partner_id

        if not cls.user_demo:
            cls.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            cls.partner_demo = cls.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            cls.user_demo = cls.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': cls.partner_demo.id,
                'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('base.group_partner_manager').id])],
            })

    @classmethod
    def _load_partners_set(cls):
        cls.partner_category = cls.env['res.partner.category'].create({
            'name': 'Sellers',
            'color': 2,
        })
        cls.partner_category_child_1 = cls.env['res.partner.category'].create({
            'name': 'Office Supplies',
            'parent_id': cls.partner_category.id,
        })
        cls.partner_category_child_2 = cls.env['res.partner.category'].create({
            'name': 'Desk Manufacturers',
            'parent_id': cls.partner_category.id,
        })

        # Load all the demo partners
        cls.partners = cls.env['res.partner'].create([
            {
                'name': 'Inner Works', # Wood Corner
                'state_id': cls.env.ref('base.state_us_1').id,
                'category_id': [(6, 0, [cls.partner_category_child_1.id, cls.partner_category_child_2.id,])],
                'child_ids': [(0, 0, {
                    'name': 'Sheila Ruiz', # 'Willie Burke',
                }), (0, 0, {
                    'name': 'Wyatt Howard', # 'Ron Gibson',
                }), (0, 0, {
                    'name': 'Austin Kennedy', # Tom Ruiz
                })],
            }, {
                'name': 'Pepper Street', # 'Deco Addict',
                'state_id': cls.env.ref('base.state_us_2').id,
                'child_ids': [(0, 0, {
                    'name': 'Liam King', # 'Douglas Fletcher',
                }), (0, 0, {
                    'name': 'Craig Richardson', # 'Floyd Steward',
                }), (0, 0, {
                    'name': 'Adam Cox', # 'Addison Olson',
                })],
            }, {
                'name': 'AnalytIQ', #'Gemini Furniture',
                'state_id': cls.env.ref('base.state_us_3').id,
                'child_ids': [(0, 0, {
                    'name': 'Pedro Boyd', # Edwin Hansen
                }), (0, 0, {
                    'name': 'Landon Roberts', # 'Jesse Brown',
                    'company_id': cls.env.ref('base.main_company').id,
                }), (0, 0, {
                    'name': 'Leona Shelton', # 'Soham Palmer',
                }), (0, 0, {
                    'name': 'Scott Kim', # 'Oscar Morgan',
                })],
            }, {
                'name': 'Urban Trends', # 'Ready Mat',
                'state_id': cls.env.ref('base.state_us_4').id,
                'category_id': [(6, 0, [cls.partner_category_child_1.id, cls.partner_category_child_2.id,])],
                'child_ids': [(0, 0, {
                    'name': 'Louella Jacobs', # 'Billy Fox',
                }), (0, 0, {
                    'name': 'Albert Alexander', # 'Kim Snyder',
                }), (0, 0, {
                    'name': 'Brad Castillo', # 'Edith Sanchez',
                }), (0, 0, {
                    'name': 'Sophie Montgomery', # 'Sandra Neal',
                }), (0, 0, {
                    'name': 'Chloe Bates', # 'Julie Richards',
                }), (0, 0, {
                    'name': 'Mason Crawford', # 'Travis Mendoza',
                }), (0, 0, {
                    'name': 'Elsie Kennedy', # 'Theodore Gardner',
                })],
            }, {
                'name': 'Ctrl-Alt-Fix', # 'The Jackson Group',
                'state_id': cls.env.ref('base.state_us_5').id,
                'child_ids': [(0, 0, {
                    'name': 'carole miller', # 'Toni Rhodes',
                }), (0, 0, {
                    'name': 'Cecil Holmes', # 'Gordon Owens',
                })],
            }, {
                'name': 'Ignitive Labs', # 'Azure Interior',
                'state_id': cls.env.ref('base.state_us_6').id,
                'child_ids': [(0, 0, {
                    'name': 'Jonathan Webb', # 'Brandon Freeman',
                }), (0, 0, {
                    'name': 'Clinton Clark', # 'Nicole Ford',
                }), (0, 0, {
                    'name': 'Howard Bryant', # 'Colleen Diaz',
                })],
            }, {
                'name': 'Amber & Forge', # 'Lumber Inc',
                'state_id': cls.env.ref('base.state_us_7').id,
                'child_ids': [(0, 0, {
                    'name': 'Mark Webb', # 'Lorraine Douglas',
                })],
            }, {
                'name': 'Rebecca Day', # 'Chester Reed',
                'parent_id': cls.env.ref('base.main_partner').id,
            }, {
                'name': 'Gabriella Jennings', # 'Dwayne Newman',
                'parent_id': cls.env.ref('base.main_partner').id,
            }
        ])

class HttpCaseWithUserPortal(HttpCase):

    def setUp(self):
        super(HttpCaseWithUserPortal, self).setUp()
        self.user_portal = self.env['res.users'].search([('login', '=', 'portal')])
        self.partner_portal = self.user_portal.partner_id

        if not self.user_portal:
            self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            self.partner_portal = self.env['res.partner'].create({
                'name': 'Joel Willis',
                'email': 'joel.willis63@example.com',
            })
            self.user_portal = self.env['res.users'].with_context(no_reset_password=True).create({
                'login': 'portal',
                'password': 'portal',
                'partner_id': self.partner_portal.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            })
