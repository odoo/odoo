""" Encode any known changes to the database here
to help the matching process
"""

renamed_modules = {
    # OCA/connector
    # Connector module has been unfolded in 2 modules in version 10.0:
    # connector and queue_job. We need to do this to correct upgrade both
    # modules.
    'connector': 'queue_job',
    # OCA/hr
    # The OCA extensions of the hr_holidays module are 'hr_holidays_something'
    'hr_holiday_notify_employee_manager': 'hr_holidays_notify_employee_manager'
}

renamed_models = {
}
