# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestViews(TransactionCase):
    def test_inherit_specific(self):
        View = self.env['ir.ui.view']
        Website = self.env['website']

        website_1 = Website.create({'name': 'Website 1'})

        # 1. Simulate COW structure
        main_view = View.create({
            'name': 'Test Main View',
            'type': 'qweb',
            'arch': '<body>Arch is not relevant for this test</body>',
            'key': '_test.main_view',
        }).with_context(load_all_views=True)
        # Trigger COW
        main_view.with_context(website_id=website_1.id).arch = '<body>specific</body>'

        # 2. Simulate a theme install with a child view of `main_view`
        test_theme_module = self.env['ir.module.module'].create({'name': 'test_theme'})
        self.env['ir.model.data'].create({
            'module': 'base',
            'name': 'module_test_theme_module',
            'model': 'ir.module.module',
            'res_id': test_theme_module.id,
        })
        theme_view = self.env['theme.ir.ui.view'].with_context(install_filename='/testviews').create({
            'name': 'Test Child View',
            'mode': 'extension',
            'inherit_id': 'ir.ui.view,%s' % main_view.id,
            'arch': '<xpath expr="//body" position="replace"><span>C</span></xpath>',
            'key': 'test_theme.test_child_view',
        })
        self.env['ir.model.data'].create({
            'module': 'test_theme',
            'name': 'products',
            'model': 'theme.ir.ui.view',
            'res_id': theme_view.id,
        })
        test_theme_module.with_context(load_all_views=True)._theme_load(website_1)

        # 3. Ensure everything went correctly
        main_views = View.search([('key', '=', '_test.main_view')])
        self.assertEqual(len(main_views), 2, "View should have been COWd when writing on its arch in a website context")
        specific_main_view = main_views.filtered(lambda v: v.website_id == website_1)
        specific_main_view_children = specific_main_view.inherit_children_ids
        self.assertEqual(specific_main_view_children.name, 'Test Child View', "Ensure theme.ir.ui.view has been loaded as an ir.ui.view into the website..")
        self.assertEqual(specific_main_view_children.website_id, website_1, "..and the website is the correct one.")


class Crawler(HttpCase):
    def test_multi_website_views_retrieving(self):
        View = self.env['ir.ui.view']
        Website = self.env['website']

        website_1 = Website.create({'name': 'Website 1'})
        website_2 = Website.create({'name': 'Website 2'})

        main_view = View.create({
            'name': 'Products',
            'type': 'qweb',
            'arch': '<body>Arch is not relevant for this test</body>',
            'key': '_website_sale.products',
        }).with_context(load_all_views=True)

        View.with_context(load_all_views=True).create({
            'name': 'Child View W1',
            'mode': 'extension',
            'inherit_id': main_view.id,
            'arch': '<xpath expr="//body" position="replace">It is really not relevant!</xpath>',
            'key': '_website_sale.child_view_w1',
            'website_id': website_1.id,
            'active': False,
            'customize_show': True,
        })

        # Simulate theme view instal + load on website
        theme_view = self.env['theme.ir.ui.view'].with_context(install_filename='/testviews').create({
            'name': 'Products Theme Kea',
            'mode': 'extension',
            'inherit_id': main_view.id,
            'arch': '<xpath expr="//p" position="replace"><span>C</span></xpath>',
            'key': '_theme_kea_sale.products',
        })
        view_from_theme_view_on_w2 = View.with_context(load_all_views=True).create({
            'name': 'Products Theme Kea',
            'mode': 'extension',
            'inherit_id': main_view.id,
            'arch': '<xpath expr="//body" position="replace">Really really not important for this test</xpath>',
            'key': '_theme_kea_sale.products',
            'website_id': website_2.id,
            'customize_show': True,
        })
        self.env['ir.model.data'].create({
            'module': '_theme_kea_sale',
            'name': 'products',
            'model': 'theme.ir.ui.view',
            'res_id': theme_view.id,
        })

        # ##################################################### ir.ui.view ###############################################
        # id |        name        | website_id | inherit |             key               |          xml_id               |
        # ----------------------------------------------------------------------------------------------------------------
        #  1 | Products           |      /     |    /    | _website_sale.products        |            /                  |
        #  2 | Child View W1      |      1     |    1    | _website_sale.child_view_w1   |            /                  |
        #  3 | Products Theme Kea |      2     |    1    | _theme_kea_sale.products      |            /                  |

        # ################################################# theme.ir.ui.view #############################################
        # id |               name              | inherit |             key               |         xml_id                |
        # ----------------------------------------------------------------------------------------------------------------
        #  1 | Products Theme Kea              |    1    | _theme_kea_sale.products      | _theme_kea_sale.products      |

        with self.assertRaises(ValueError):
            # It should crash as it should not find a view on website 1 for '_theme_kea_sale.products', !!and certainly not a theme.ir.ui.view!!.
            view = View.with_context(website_id=website_1.id)._view_obj('_theme_kea_sale.products')
        view = View.with_context(website_id=website_2.id)._view_obj('_theme_kea_sale.products')
        self.assertEquals(len(view), 1, "It should find the ir.ui.view with key '_theme_kea_sale.products' on website 2..")
        self.assertEquals(view._name, 'ir.ui.view', "..and not a theme.ir.ui.view")

        views = View.with_context(website_id=website_1.id).get_related_views('_website_sale.products')
        self.assertEquals(len(views), 2, "It should not mix apples and oranges, only ir.ui.view ['_website_sale.products', '_website_sale.child_view_w1'] should be returned")
        views = View.with_context(website_id=website_2.id).get_related_views('_website_sale.products')
        self.assertEquals(len(views), 2, "It should not mix apples and oranges, only ir.ui.view ['_website_sale.products', '_theme_kea_sale.products'] should be returned")

        # Part 2 of the test, it test the same stuff but from a higher level (get_related_views ends up calling _view_obj)
        called_theme_view = self.env['theme.ir.ui.view'].with_context(install_filename='/testviews').create({
            'name': 'Called View Kea',
            'arch': '<div></div>',
            'key': '_theme_kea_sale.t_called_view',
        })
        View.create({
            'name': 'Called View Kea',
            'type': 'qweb',
            'arch': '<div></div>',
            'key': '_theme_kea_sale.t_called_view',
            'website_id': website_2.id,
        }).with_context(load_all_views=True)
        self.env['ir.model.data'].create({
            'module': '_theme_kea_sale',
            'name': 't_called_view',
            'model': 'theme.ir.ui.view',
            'res_id': called_theme_view.id,
        })
        view_from_theme_view_on_w2.write({'arch': '<t t-call="_theme_kea_sale.t_called_view"/>'})

        # ##################################################### ir.ui.view ###############################################
        # id |        name        | website_id | inherit |             key               |          xml_id               |
        # ----------------------------------------------------------------------------------------------------------------
        #  1 | Products           |      /     |    /    | _website_sale.products        |            /                  |
        #  2 | Child View W1      |      1     |    1    | _website_sale.child_view_w1   |            /                  |
        #  3 | Products Theme Kea |      2     |    1    | _theme_kea_sale.products      |            /                  |
        #  4 | Called View Kea    |      2     |    /    | _theme_kea_sale.t_called_view |            /                  |

        # ################################################# theme.ir.ui.view #############################################
        # id |               name              | inherit |             key               |         xml_id                |
        # ----------------------------------------------------------------------------------------------------------------
        #  1 | Products Theme Kea              |    1    | _theme_kea_sale.products      | _theme_kea_sale.products      |
        #  1 | Called View Kea                 |    /    | _theme_kea_sale.t_called_view | _theme_kea_sale.t_called_view |

        # Next line should not crash (was mixing apples and oranges - ir.ui.view and theme.ir.ui.view)
        views = View.with_context(website_id=website_1.id).get_related_views('_website_sale.products')
        self.assertEquals(len(views), 2, "It should not mix apples and oranges, only ir.ui.view ['_website_sale.products', '_website_sale.child_view_w1'] should be returned (2)")
        views = View.with_context(website_id=website_2.id).get_related_views('_website_sale.products')
        self.assertEquals(len(views), 3, "It should not mix apples and oranges, only ir.ui.view ['_website_sale.products', '_theme_kea_sale.products', '_theme_kea_sale.t_called_view'] should be returned")

        # ########################################################
        # Test the controller (which is calling get_related_views)
        self.authenticate("admin", "admin")
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        # Simulate website 2
        url = base_url + '/website/force_website'
        json = {'params': {'website_id': website_2.id}}
        self.opener.post(url=url, json=json)

        # Test controller
        url = base_url + '/website/get_switchable_related_views'
        json = {'params': {'key': '_website_sale.products'}}
        response = self.opener.post(url=url, json=json)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['result']), 1, "Only '_theme_kea_sale.products' should be returned as it is the only customize_show related view in website 2 context")
        self.assertEqual(response.json()['result'][0]['key'], '_theme_kea_sale.products', "Only '_theme_kea_sale.products' should be returned")

        # Simulate website 1
        url = base_url + '/website/force_website'
        json = {'params': {'website_id': website_1.id}}
        self.opener.post(url=url, json=json)

        # Test controller
        url = base_url + '/website/get_switchable_related_views'
        json = {'params': {'key': '_website_sale.products'}}
        response = self.opener.post(url=url, json=json)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['result']), 1, "Only '_website_sale.child_view_w1' should be returned as it is the only customize_show related view in website 1 context")
        self.assertEqual(response.json()['result'][0]['key'], '_website_sale.child_view_w1', "Only '_website_sale.child_view_w1' should be returned")
