# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Vishnu P(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'Theme Eco Refine',
    'version': '16.0.1.0.0',
    'category': 'Theme/eCommerce',
    'summary': 'Theme Eco Refine',
    'description': 'Theme Eco Refine module provide attractive and unique '
                    'front end theme mainly suitable for eCommerce website',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    "depends": ['base', 'web', 'website', 'website_livechat',
                 'website_sale_wishlist', 'website_blog', ],
    'data': [
         'data/theme_eco_refine_menus.xml',
         'views/product_template_views.xml',
         'views/website_blog_templates.xml',
         'views/templates.xml',
         'static/src/xml/homepage_templates.xml',
         'views/snippets.xml',
         'views/about_us_templates.xml'
    ],
    'assets': {
        'web.assets_frontend': [
             'https://code.jquery.com/jquery-3.2.1.slim.min.js',
             'https://cdn.jsdelivr.net/npm/popper.js@1.12.9/dist/umd/popper.min.js',
             'https://cdn.jsdelivr.net/npm/bootstrap@4.0.0/dist/js/bootstrap.min.js',
             'theme_eco_refine/static/src/css/contact_us.css',
             'theme_eco_refine/static/src/css/product.css',
             'theme_eco_refine/static/src/css/home.css',
             'theme_eco_refine/static/src/css/blog.css',
             'theme_eco_refine/static/src/js/product_specification.js',
             'theme_eco_refine/static/src/css/about_us.css',
             'theme_eco_refine/static/src/js/about_us.js',
             'theme_eco_refine/static/src/js/owl.carousel.js',
             'theme_eco_refine/static/src/js/owl.carousel.min.js',
             'theme_eco_refine/static/src/css/owl.carousel.css',
             'theme_eco_refine/static/src/js/collection_snippet.js',
             'theme_eco_refine/static/src/js/refurbished_carousel_snippet.js',
             'theme_eco_refine/static/src/js/best_seller_snippet.js',
             'theme_eco_refine/static/src/xml/best_seller_snippet_templates.xml',
             'theme_eco_refine/static/src/js/new_arrival_snippet.js',
             'theme_eco_refine/static/src/xml/new_arrival_snippet_templates.xml',
             'theme_eco_refine/static/src/js/customer_response.js',
             'theme_eco_refine/static/src/js/top_rated_products_snippet.js',
             'theme_eco_refine/static/src/xml/top_rated_product_snippet_templates.xml',
        ],
     },
    'images': [
         'static/description/banner.png',
         'static/description/theme_screenshot.jpg',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
 }
