{
    "name": "Auto-Info Recognition & Belonging",
    "summary": "Kudos wall, birthdays and work anniversaries for the employee portal",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "The Auto-Info Co., Ltd.",
    "website": "https://www.auto-info.co.th",
    "license": "LGPL-3",
    "depends": [
        "od19_website",
        "hr",
        "mail",
        "portal",
    ],
    "data": [
        "security/od19_recognition_security.xml",
        "security/ir.model.access.csv",
        "data/od19_recognition_badge_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
