{
    "name": "OD19 Web Navigation (Back / Forward)",
    "version": "19.0.1.0.0",
    "summary": "ปุ่มย้อนกลับ / ไปข้างหน้า ในแถบ Systray ของ Odoo 19 Backend (สไตล์ Liquid Glass) พร้อมคีย์ลัด Alt+← / Alt+→",
    "author": "The Auto-Info Co., Ltd.",
    "website": "https://www.auto-info.co.th",
    "license": "LGPL-3",
    "category": "Productivity",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "od19_web_navigation/static/src/js/od19_nav_history.js",
            "od19_web_navigation/static/src/js/od19_nav_buttons.js",
            "od19_web_navigation/static/src/css/od19_nav_buttons.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
