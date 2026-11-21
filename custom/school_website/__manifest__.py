{
    "name": "Harvard University Website",
    "version": "19.0.1.0.0",
    "category": "Website/Education",
    "summary": "Harvard University Public Portal, Programs Directory, Admissions, Events & AI Chatbot",
    "author": "Harvard University",
    "license": "LGPL-3",
    "depends": [
        "website",
        "school_management",
        "im_livechat",
    ],
    "data": [
        "data/website_menu_data.xml",
        "data/chatbot_data.xml",
        "views/website/website_templates.xml",
        "views/academic/courses_templates.xml",
        "views/admission/admission_templates.xml",
        "views/dashboard/events_templates.xml",
        "views/core/jobs_templates.xml",
        "views/core/about_templates.xml",
        "views/core/contact_templates.xml",
        "views/chatbot/chatbot_script_views.xml",
        "views/chatbot/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "school_website/static/src/scss/school_website.scss",
            "school_website/static/src/js/chatbot_ai_patch.js",
        ],
        "im_livechat.assets_embed_core": [
            "school_website/static/src/js/chatbot_ai_patch.js",
        ],
        "mail.assets_public": [
            "school_website/static/src/js/chatbot_ai_patch.js",
        ],
    },
    "installable": True,
    "application": True,
}
