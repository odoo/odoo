{
    'name': "HR Contract Timesheet Holidays",
    'summary': "Bridge module linking HR Contract and Project Timesheet Holidays modules",
    'description': """
        HR Contract Timesheet Holidays
        =================================

        This module serves as a bridge between the HR Contract module and the Project Timesheet Holidays module.
        It ensures synchronization and accurate linkage of employee contracts with holiday-related timesheets.
    """,
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['project_timesheet_holidays', 'hr_contract'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
