{
    "name": "eLearning",
    "version": "2.10",
    "category": "Website/eLearning",
    "sequence": 125,
    "summary": "Manage and publish an eLearning platform",
    "description": """
Create Online Courses
=====================

Featuring

 * Integrated course and lesson management
 * Fullscreen navigation
 * Support Youtube videos, Google documents, PDF, images, articles
 * Test knowledge with quizzes
 * Filter and Tag
 * Statistics
""",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/elearning",
    "license": "LGPL-3",
    "depends": [
        "portal_rating",
        "survey",
        "website",
        "website_mail",
        "website_profile",
        "approval",
    ],
    "data": [
        "security/website_slides_security.xml",
        "security/ir.model.access.csv",
        "views/gamification_karma_tracking_views.xml",
        "views/mail_activity_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/rating_rating_views.xml",
        "views/slide_embed_views.xml",
        "views/slide_slide_partner_views.xml",
        "views/slide_slide_views.xml",
        "views/slide_channel_partner_views.xml",
        "views/slide_channel_views.xml",
        "views/slide_channel_tag_views.xml",
        "views/website_slides_templates_homepage.xml",
        "views/website_slides_templates_course.xml",
        "views/website_slides_templates_lesson.xml",
        "views/website_slides_templates_lesson_fullscreen.xml",
        "views/website_slides_templates_lesson_embed.xml",
        "views/website_slides_templates_profile.xml",
        "views/website_slides_templates_utils.xml",
        "views/website_pages_views.xml",
        "views/slide_channel_add.xml",
        "wizards/slide_channel_invite_views.xml",
        "data/gamification_data.xml",
        "data/mail_message_subtype_data.xml",
        "data/mail_template_data.xml",
        "data/mail_templates.xml",
        "data/slide_data.xml",
        "data/approval_category_data.xml",
        "data/website_data.xml",
        "data/slides_tour.xml",
        "views/website_slides_menu_views.xml",
    ],
    "demo": [
        "demo/res_users_demo.xml",
        "demo/slide_channel_tag_demo.xml",
        "demo/slide_channel_demo.xml",
        "demo/slide_slide_demo.xml",
        "demo/slide_user_demo.xml",
        "demo/slide_user_gamification_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "website_slides/static/src/activity/**/*",
            "website_slides/static/src/slide_category_one2many_field.js",
            "website_slides/static/src/slide_category_list_renderer.js",
            "website_slides/static/src/scss/slide_views.scss",
            "website_slides/static/src/js/tours/slides_tour.js",
            "website_slides/static/src/js/components/**/*.js",
            "website_slides/static/src/views/**/*.js",
            "website_slides/static/src/views/**/*.xml",
        ],
        "web.assets_frontend": [
            "website_slides/static/src/interactions/**/*",
            "website_slides/static/src/scss/website_slides.scss",
            "website_slides/static/src/scss/website_slides_profile.scss",
            "website_slides/static/src/scss/slides_slide_fullscreen.scss",
            "website_slides/static/src/xml/website_slides_sidebar.xml",
            "website_slides/static/src/xml/website_slides_fullscreen.xml",
            "website_slides/static/src/xml/slide_management.xml",
            "website_slides/static/src/xml/slide_course_join.xml",
            "website_slides/static/src/xml/slide_course_prerequisite.xml",
            "website_slides/static/src/xml/slide_quiz_create.xml",
            "website_slides/static/src/xml/slide_quiz.xml",
            "website_slides/static/src/js/public/**/*",
        ],
        "website.assets_editor": [
            "website_slides/static/src/js/systray_items/*.js",
        ],
        "web.assets_tests": [
            "website_slides/static/tests/tours/*.js",
        ],
        "website_slides.slide_embed_assets": [
            (
                "include",
                "web._assets_helpers",
            ),
            (
                "include",
                "web._assets_frontend_helpers",
            ),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "web/static/lib/bootstrap/scss/_variables-dark.scss",
            "web/static/lib/bootstrap/scss/_maps.scss",
            (
                "include",
                "web._assets_bootstrap_frontend",
            ),
            "web/static/src/scss/tokens.scss",
            "web/static/src/libs/fontawesome7/css/fontawesome.css",
            "web/static/src/libs/fontawesome7/css/solid.css",
            "web/static/src/libs/fontawesome7/css/regular.css",
            "web/static/src/libs/fontawesome7/css/brands.css",
            "web/static/lib/odoo_ui_icons/*",
            "web/static/src/webclient/navbar/navbar.scss",
            "web/static/src/scss/animation.scss",
            "web/static/src/scss/rtl_icon_flip.scss",
            "web/static/src/scss/mimetypes.scss",
            "web/static/src/scss/ui.scss",
            "web/static/src/components/color_picker/color_picker.scss",
            "web/static/src/fields/translation_dialog.scss",
            "web/static/src/fields/media/signature/signature_field.scss",
            "website/static/src/libs/zoomodoo/zoomodoo.scss",
            "web/static/src/session.js",
            "web/static/src/libs/bootstrap.js",
            "website/static/src/libs/zoomodoo/zoomodoo.js",
            "web/static/src/core/**/*.js",
            "web/static/src/env.js",
            "website_slides/static/src/scss/website_slides.scss",
            "website_slides/static/lib/pdfslidesviewer/PDFSlidesViewer.js",
            "website_slides/static/src/js/slides_embed.js",
        ],
        "web.assets_unit_tests": [
            "website_slides/static/tests/**/*",
            (
                "remove",
                "website_slides/static/tests/tours/**/*",
            ),
        ],
        "web.assets_unit_tests_setup": [
            "website_slides/static/src/interactions/**/*",
            "website_slides/static/src/js/public/**/*",
        ],
        "website.website_builder_assets": [
            "website_slides/static/src/website_builder/**/*",
        ],
        "portal.assets_chatter": [
            "website_slides/static/src/chatter/frontend/**/*",
        ],
    },
    "esm": {
        "bundles": [
            "website_slides.slide_embed_assets",
        ],
    },
    "application": True,
}
