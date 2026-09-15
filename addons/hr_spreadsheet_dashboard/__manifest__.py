{
    'name': 'Employees Spreadsheet Dashboard',
    'version': '1.0',
    'category': 'Employees',
    'description': """
Bridge module between HR (Employees) and Spreadsheet Dashboard.
Ensures employee data sources dynamically reflect the active company context.
    """,
    'depends': ['hr', 'spreadsheet_dashboard'],
    'auto_install': True,
    'license': 'LGPL-3',
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'hr_spreadsheet_dashboard/static/src/spreadsheet/**/*',
        ],
        'web.assets_unit_tests': [
            'hr_spreadsheet_dashboard/static/tests/**/*',
        ],
    },
}
