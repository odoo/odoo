{
    "name": "Employee Portal",
    "summary": "Employee board and task management",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Your Name",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "mail", "hr"],  # ← 必ずリストで書く
    "data": [
        "security/employee_portal_security.xml",
        "security/ir.model.access.csv",
        "views/employee_board_views.xml",
        "views/employee_task_views.xml",
        "views/employee_portal_menu.xml",
        "data/employee_task_cron.xml",
    ],
    "installable": True,   # ← インストール可能にする
    "application": True,   # ← Apps 画面に表示させる
}
