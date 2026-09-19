{
    "name": "Quizzes on Tracks",
    "version": "1.1",
    "category": "Marketing/Events",
    "sequence": 1007,
    "summary": "Quizzes on tracks",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/events",
    "license": "LGPL-3",
    "depends": [
        "website_profile",
        "website_event_track",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/event_leaderboard_templates.xml",
        "views/event_quiz_views.xml",
        "views/event_quiz_question_views.xml",
        "views/event_track_views.xml",
        "views/event_track_visitor_views.xml",
        "views/event_menus.xml",
        "views/event_quiz_templates.xml",
        "views/event_track_templates_page.xml",
        "views/event_event_views.xml",
        "views/event_type_views.xml",
    ],
    "demo": [
        "demo/quiz_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_event_track_quiz/static/src/scss/event_quiz.scss",
            "website_event_track_quiz/static/src/interactions/**/*",
            "website_event_track_quiz/static/src/xml/quiz_templates.xml",
        ],
    },
}
