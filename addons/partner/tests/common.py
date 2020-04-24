
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class SavepointCaseWithPartnersSet(SavepointCaseWithUserDemo):

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
