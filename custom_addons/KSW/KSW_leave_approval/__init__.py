from . import models

def post_init_hook(env):
    # Set validation_type to 'both' for all non-annual leave types
    # to ensure they follow the 2nd approval step requirement.
    non_annual_types = env['hr.leave.type'].search([('is_annual_leave', '=', False)])
    non_annual_types.write({'leave_validation_type': 'both'})
