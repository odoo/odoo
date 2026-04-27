{
    'name': "Time off Gantt",
    'summary': """Gantt view for Time Off Dashboard""",
    'description': """
    Gantt view for Time Off Dashboard
    """,
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['hr_holidays', 'web_gantt'],
    'auto_install': True,
    'data': [
        'views/hr_holidays_gantt_view.xml',
    ],
    'assets': {
        'web.assets_backend_lazy': [
            'hr_holidays_gantt/static/src/**/*',
        ],
    },
    'license': 'OEEL-1',
}
