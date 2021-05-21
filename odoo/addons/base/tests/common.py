# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase, TransactionCase, HttpCase


class PostEnvHook:
    """Mixin allowing to create mixins adding a feature in the setUp or the setUpClass of a test case."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if hasattr(cls, 'env'):
            cls._post_env_hook(cls)

    def setUp(self):
        super().setUp()
        if not hasattr(type(self), 'env'):
            self._post_env_hook(self)

    @classmethod
    def _post_env_hook(cls, self_or_cls):
        pass


class WithUserDemo(PostEnvHook):
    @classmethod
    def _post_env_hook(cls, self_or_cls):
        super()._post_env_hook(self_or_cls)
        cls._setup_user_demo(self_or_cls)

    @classmethod
    def _setup_user_demo(cls, self_or_cls):
        self_or_cls.user_admin = self_or_cls.env.ref('base.user_admin')
        self_or_cls.user_admin.write({'name': 'Mitchell Admin'})
        self_or_cls.partner_admin = self_or_cls.user_admin.partner_id
        self_or_cls.user_demo = self_or_cls.env['res.users'].search([('login', '=', 'demo')])
        self_or_cls.partner_demo = self_or_cls.user_demo.partner_id

        if not self_or_cls.user_demo:
            self_or_cls.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            # YTI TODO: This could be factorized between the different classes
            self_or_cls.partner_demo = self_or_cls.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            self_or_cls.user_demo = self_or_cls.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': self_or_cls.partner_demo.id,
                'groups_id': [(6, 0, [self_or_cls.env.ref('base.group_user').id, self_or_cls.env.ref('base.group_partner_manager').id])],
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

class WithUserPortal(PostEnvHook):
    @classmethod
    def _post_env_hook(cls, self_or_cls):
        super()._post_env_hook(self_or_cls)
        cls._setup_user_portal(self_or_cls)

    @classmethod
    def _setup_user_portal(cls, self_or_cls):
        self_or_cls.user_portal = self_or_cls.env['res.users'].sudo().search([('login', '=', 'portal')])
        self_or_cls.partner_portal = self_or_cls.user_portal.partner_id

        if not self_or_cls.user_portal:
            self_or_cls.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            self_or_cls.partner_portal = self_or_cls.env['res.partner'].create({
                'name': 'Joel Willis',
                'email': 'joel.willis63@example.com',
            })
            self_or_cls.user_portal = self_or_cls.env['res.users'].with_context(no_reset_password=True).create({
                'login': 'portal',
                'password': 'portal',
                'partner_id': self_or_cls.partner_portal.id,
                'groups_id': [(6, 0, [self_or_cls.env.ref('base.group_portal').id])],
            })


class TransactionCaseWithUserDemo(WithUserDemo, TransactionCase):
    pass


class HttpCaseWithUserDemo(WithUserDemo, HttpCase):
    pass


class SavepointCaseWithUserDemo(WithUserDemo, SavepointCase):
    pass


class HttpCaseWithUserPortal(WithUserPortal, HttpCase):
    pass
