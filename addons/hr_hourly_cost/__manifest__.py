{
    "name": "Employee Hourly Cost",
    "version": "1.2",
    "category": "Services/Timesheets",
    "summary": "Hourly cost of an employee's work, for other modules to value time",
    "description": """
Gives every employee an hourly cost, so that a module valuing worked time --
timesheets, attendances, work orders, planning -- has one number to read
instead of inventing its own.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr",
    ],
    "data": [
        "views/hr_employee_views.xml",
    ],
    "demo": [
        "demo/hr_hourly_cost_demo.xml",
    ],
}
