# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website',
    'category': 'Website/Website',
    'sequence': 20,
    'summary': 'Enterprise website builder',
    'website': 'https://www.odoo.com/page/website-builder',
    'version': '1.0',
    'description': "",
    'depends': [
        'digest',
        'web',
        'web_editor',
        'http_routing',
        'portal',
        'social_media',
        'auth_signup',
    ],
    'installable': True,
    'data': [
        'data/ir_asset.xml',
        'data/website_data.xml',
        'data/website_visitor_cron.xml',
        'security/website_security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'views/assets.xml',
        'views/website_templates.xml',
        'views/website_navbar_templates.xml',
        'views/snippets/snippets.xml',
        'views/snippets/s_title.xml',
        'views/snippets/s_cover.xml',
        'views/snippets/s_text_image.xml',
        'views/snippets/s_image_text.xml',
        'views/snippets/s_banner.xml',
        'views/snippets/s_text_block.xml',
        'views/snippets/s_features.xml',
        'views/snippets/s_three_columns.xml',
        'views/snippets/s_picture.xml',
        'views/snippets/s_carousel.xml',
        'views/snippets/s_alert.xml',
        'views/snippets/s_card.xml',
        'views/snippets/s_share.xml',
        'views/snippets/s_rating.xml',
        'views/snippets/s_hr.xml',
        'views/snippets/s_facebook_page.xml',
        'views/snippets/s_image_gallery.xml',
        'views/snippets/s_countdown.xml',
        'views/snippets/s_product_catalog.xml',
        'views/snippets/s_comparisons.xml',
        'views/snippets/s_company_team.xml',
        'views/snippets/s_call_to_action.xml',
        'views/snippets/s_references.xml',
        'views/snippets/s_popup.xml',
        'views/snippets/s_faq_collapse.xml',
        'views/snippets/s_features_grid.xml',
        'views/snippets/s_tabs.xml',
        'views/snippets/s_table_of_content.xml',
        'views/snippets/s_chart.xml',
        'views/snippets/s_parallax.xml',
        'views/snippets/s_quotes_carousel.xml',
        'views/snippets/s_numbers.xml',
        'views/snippets/s_masonry_block.xml',
        'views/snippets/s_media_list.xml',
        'views/snippets/s_showcase.xml',
        'views/snippets/s_timeline.xml',
        'views/snippets/s_process_steps.xml',
        'views/snippets/s_text_highlight.xml',
        'views/snippets/s_progress_bar.xml',
        'views/snippets/s_blockquote.xml',
        'views/snippets/s_badge.xml',
        'views/snippets/s_color_blocks_2.xml',
        'views/snippets/s_product_list.xml',
        'views/snippets/s_mega_menu_multi_menus.xml',
        'views/snippets/s_mega_menu_menu_image_menu.xml',
        'views/snippets/s_google_map.xml',
        'views/snippets/s_dynamic_snippet.xml',
        'views/snippets/s_dynamic_snippet_carousel.xml',
        'views/website_views.xml',
        'views/website_visitor_views.xml',
        'views/res_config_settings_views.xml',
        'views/website_rewrite.xml',
        'views/ir_actions_views.xml',
        'views/ir_asset_views.xml',
        'views/ir_attachment_views.xml',
        'views/res_partner_views.xml',
        'wizard/base_language_install_views.xml',
        'wizard/website_robots.xml',

        # Old snippets
        ],
    'demo': [
        'data/website_demo.xml',
    ],
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            # after //link[last()]
            'website/static/src/snippets/s_media_list/001.scss',
            # after //link[last()]
            'website/static/src/snippets/s_color_blocks_2/000.scss',
            # after //script[last()]
            'website/static/src/snippets/s_chart/000.js',
            # after //link[last()]
            'website/static/src/snippets/s_masonry_block/001.scss',
            # after //link[last()]
            'website/static/src/snippets/s_rating/001.scss',
            # after //link[last()]
            'website/static/src/snippets/s_dynamic_snippet_carousel/000.scss',
            # after //script[last()]
            'website/static/src/snippets/s_dynamic_snippet_carousel/000.js',
            # after //link[last()]
            'website/static/src/snippets/s_references/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_alert/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_image_gallery/001.scss',
            # after //script[last()]
            'website/static/src/snippets/s_image_gallery/000.js',
            # None None
            # There is no content in this asset...
            # after //script[last()]
            'website/static/src/snippets/s_facebook_page/000.js',
            # after //link[last()]
            'website/static/src/snippets/s_timeline/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_product_list/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_process_steps/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_company_team/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_product_catalog/001.scss',
            # after //script[last()]
            'website/static/src/snippets/s_countdown/000.js',
            # None None
            # There is no content in this asset...
            # after //link[last()]
            'website/static/src/snippets/s_badge/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_dynamic_snippet/000.scss',
            # after //script[last()]
            'website/static/src/snippets/s_dynamic_snippet/000.js',
            # after //link[last()]
            'website/static/src/snippets/s_tabs/001.scss',
            # after //link[last()]
            'website/static/src/snippets/s_features_grid/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_blockquote/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_card/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_btn/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_table_of_content/000.scss',
            # after //script[last()]
            'website/static/src/snippets/s_table_of_content/000.js',
            # after //link[last()]
            'website/static/src/snippets/s_share/000.scss',
            # after //script[last()]
            'website/static/src/snippets/s_share/000.js',
            # after //link[last()]
            'website/static/src/snippets/s_text_highlight/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_quotes_carousel/001.scss',
            # after //link[last()]
            'website/static/src/snippets/s_google_map/000.scss',
            # after //script[last()]
            'website/static/src/snippets/s_google_map/000.js',
            # after //link[last()]
            'website/static/src/snippets/s_popup/001.scss',
            # after //script[last()]
            'website/static/src/snippets/s_popup/000.js',
            # after //link[last()]
            'website/static/src/snippets/s_faq_collapse/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_comparisons/000.scss',
            # after //link[last()]
            'website/static/src/snippets/s_hr/000.scss',
            # replace //script[@src='/web/static/src/js/public/public_root_instance.js']
            ('replace', 'web/static/src/js/public/public_root_instance.js', 'website/static/src/js/content/website_root_instance.js'),
            # after //link[last()]
            'website/static/src/scss/website.scss',
            # after //link[last()]
            'website/static/src/scss/website.ui.scss',
            # after //script[last()]
            'website/static/src/js/set_view_track.js',
            # after //script[last()]
            'website/static/src/js/utils.js',
            # after //script[last()]
            'website/static/src/js/content/website_root.js',
            # after //script[last()]
            'website/static/src/js/content/compatibility.js',
            # after //script[last()]
            'website/static/src/js/content/menu.js',
            # after //script[last()]
            'website/static/src/js/content/snippets.animation.js',
            # after //script[last()]
            'website/static/src/js/menu/navbar.js',
            # after //script[last()]
            'website/static/src/js/show_password.js',
            # after //script[last()]
            'website/static/src/js/post_link.js',
            # after //script[last()]
            'website/static/src/js/user_custom_javascript.js',
        ],
        'web._assets_primary_variables': [
            # after //link[last()]
            'website/static/src/snippets/s_product_list/000_variables.scss',
            # after //link[last()]
            'website/static/src/snippets/s_badge/000_variables.scss',
            # after //link[last()]
            'website/static/src/scss/primary_variables.scss',
            # after //link[last()]
            'website/static/src/scss/options/user_values.scss',
            # after //link[last()]
            'website/static/src/scss/options/colors/user_color_palette.scss',
            # after //link[last()]
            'website/static/src/scss/options/colors/user_theme_color_palette.scss',
        ],
        'web._assets_secondary_variables': [
            # before //link
            ('prepend', 'website/static/src/scss/secondary_variables.scss'),
        ],
        'web.assets_tests': [
            # inside .
            'website/static/tests/tours/reset_password.js',
            # inside .
            'website/static/tests/tours/rte.js',
            # inside .
            'website/static/tests/tours/html_editor.js',
            # inside .
            'website/static/tests/tours/restricted_editor.js',
            # inside .
            'website/static/tests/tours/dashboard_tour.js',
            # inside .
            'website/static/tests/tours/specific_website_editor.js',
            # inside .
            'website/static/tests/tours/public_user_editor.js',
            # inside .
            'website/static/tests/tours/website_navbar_menu.js',
            # inside .
            'website/static/tests/tours/snippet_version.js',
            # inside .
            'website/static/tests/tours/website_style_edition.js',
            # inside .
            'website/static/tests/tours/snippet_empty_parent_autoremove.js',
        ],
        'web.assets_backend': [
            # after //link[last()]
            'website/static/src/scss/website.backend.scss',
            # after //link[last()]
            'website/static/src/scss/website_visitor_views.scss',
            # after //link[last()]
            'website/static/src/scss/website.theme_install.scss',
            # after //script[last()]
            'website/static/src/js/backend/button.js',
            # after //script[last()]
            'website/static/src/js/backend/dashboard.js',
            # after //script[last()]
            'website/static/src/js/backend/res_config_settings.js',
            # after //script[last()]
            'website/static/src/js/widget_iframe.js',
            # after //script[last()]
            'website/static/src/js/theme_preview_kanban.js',
            # after //script[last()]
            'website/static/src/js/theme_preview_form.js',
        ],
        'web.qunit_suite_tests': [
            # after //script[last()]
            'website/static/tests/dashboard_tests.js',
            # after //script[last()]
            'website/static/tests/website_tests.js',
        ],
        'web._assets_frontend_helpers': [
            # before //link
            ('prepend', 'website/static/src/scss/bootstrap_overridden.scss'),
        ],
        'website.assets_wysiwyg': [
            # None None
            ('include', 'web._assets_helpers'),
            # new asset template 
            'web_editor/static/src/scss/bootstrap_overridden.scss',
            # new asset template 
            'web/static/lib/bootstrap/scss/_variables.scss',
            # new asset template 
            'website/static/src/scss/website.wysiwyg.scss',
            # new asset template 
            'website/static/src/scss/website.edit_mode.scss',
            # new asset template 
            'website/static/src/js/editor/editor.js',
            # new asset template 
            'website/static/src/js/editor/snippets.editor.js',
            # new asset template 
            'website/static/src/js/editor/rte.summernote.js',
            # new asset template 
            'website/static/src/js/editor/snippets.options.js',
            # new asset template 
            'website/static/src/snippets/s_facebook_page/options.js',
            # new asset template 
            'website/static/src/snippets/s_image_gallery/options.js',
            # new asset template 
            'website/static/src/snippets/s_countdown/options.js',
            # new asset template 
            'website/static/src/snippets/s_popup/options.js',
            # new asset template 
            'website/static/src/snippets/s_product_catalog/options.js',
            # new asset template 
            'website/static/src/snippets/s_chart/options.js',
            # new asset template 
            'website/static/src/snippets/s_rating/options.js',
            # new asset template 
            'website/static/src/snippets/s_tabs/options.js',
            # new asset template 
            'website/static/src/snippets/s_progress_bar/options.js',
            # new asset template 
            'website/static/src/snippets/s_blockquote/options.js',
            # new asset template 
            'website/static/src/snippets/s_showcase/options.js',
            # new asset template 
            'website/static/src/snippets/s_table_of_content/options.js',
            # new asset template 
            'website/static/src/snippets/s_timeline/options.js',
            # new asset template 
            'website/static/src/snippets/s_media_list/options.js',
            # new asset template 
            'website/static/src/snippets/s_google_map/options.js',
            # new asset template 
            'website/static/src/snippets/s_dynamic_snippet/options.js',
            # new asset template 
            'website/static/src/snippets/s_dynamic_snippet_carousel/options.js',
            # new asset template 
            'website/static/src/js/editor/wysiwyg_multizone.js',
            # new asset template 
            'website/static/src/js/editor/wysiwyg_multizone_translate.js',
            # new asset template 
            'website/static/src/js/editor/widget_link.js',
            # new asset template 
            'website/static/src/js/widgets/media.js',
        ],
        'website.assets_editor': [
            # None None
            ('include', 'web._assets_helpers'),
            # new asset template 
            'web/static/lib/bootstrap/scss/_variables.scss',
            # new asset template 
            'website/static/src/scss/website.editor.ui.scss',
            # new asset template 
            'website/static/src/scss/website.theme_install.scss',
            # new asset template 
            'website/static/src/js/editor/editor_menu.js',
            # new asset template 
            'website/static/src/js/editor/editor_menu_translate.js',
            # new asset template 
            'website/static/src/js/menu/content.js',
            # new asset template 
            'website/static/src/js/menu/customize.js',
            # new asset template 
            'website/static/src/js/menu/debug_manager.js',
            # new asset template 
            'website/static/src/js/menu/edit.js',
            # new asset template 
            'website/static/src/js/menu/mobile_view.js',
            # new asset template 
            'website/static/src/js/menu/new_content.js',
            # new asset template 
            'website/static/src/js/menu/seo.js',
            # new asset template 
            'website/static/src/js/menu/translate.js',
            # new asset template 
            'website/static/src/js/tours/homepage.js',
            # new asset template 
            'website/static/src/js/tours/tour_utils.js',
            # new asset template 
            'website/static/src/js/widgets/ace.js',
        ],
        'web.assets_qweb': [
            'website/static/src/xml/website.backend.xml',
            'website/static/src/xml/website_widget.xml',
            'website/static/src/xml/theme_preview.xml',
        ],
    }
}
