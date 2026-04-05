# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'Theme Medicate',
    'version': '19.0.1.0.0',
    'category': 'Theme/eCommerce',
    'summary': 'Theme  Medicate for Odoo Website and e-Commerce',
    'description': 'Custom Designed Snippets for better user experience. '
                   'Optimized Code Snippets for Enhanced User Experience.',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['base','website','website_blog'],
    'data': [
        'views/header_templates.xml',
        'views/footer_templates.xml',
        'views/about_us_views.xml',
        'views/blog_views.xml',
        'views/services_views.xml',
        'views/blog_details.xml',
        'views/contactus_views.xml',
        'views/snippets/home_page_carousel_template.xml',
        'views/snippets/home_page_about_template.xml',
        'views/snippets/home_page_facility_provided_template.xml',
        'views/snippets/home_page_about_content_template.xml',
        'views/snippets/home_page_great_work_template.xml',
        'views/snippets/home_page_working_progress_template.xml',
        'views/snippets/home_page_heart_specialists_template.xml',
        'views/snippets/home_page_clients_template.xml',
        'views/snippets/about_us_banner_template.xml',
        'views/snippets/about_us_content_template.xml',
        'views/snippets/about_us_main_service_template.xml',
        'views/snippets/about_us_count_template.xml',
        'views/snippets/about_us_work_best_process_template.xml',
        'views/snippets/services_banner_template.xml',
        'views/snippets/services_container_template.xml',
        'views/snippets/blog_banner.xml',
        'views/snippets/blog_container_snippet.xml',
        'views/snippets/contactus_banner.xml',
        'views/snippets/contactus_snippet.xml',
        'views/snippets/contactus_map.xml',
        'views/snippets.xml',
        'views/homepage_snippets.xml',
    ],
    'assets': {
            'web.assets_frontend': [
                "https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css",
                "https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js",
                "theme_medicate/static/src/js/swiper.js",
                "theme_medicate/static/src/js/read_more.js",
                "theme_medicate/static/src/css/main.css",
                'theme_medicate/static/src/js/blog_search.js',
            ],
    },
    'images': [
            'static/description/banner.jpg',
            'static/description/theme_screenshot.jpg',
        ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
