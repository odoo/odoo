# HR Timesheet - Read-only for Users

## Overview

This module restricts timesheet editing permissions to administrators only. Standard users can view their own timesheets but cannot create, edit, or delete them.

## Features

- **Standard Users (`User: own timesheets only` group)**:
  - Can view their own timesheets (read-only)
  - Cannot create new timesheets
  - Cannot edit existing timesheets
  - Cannot delete timesheets

- **Administrators (`Timesheet Manager` group)**:
  - Full access to all timesheets
  - Can create, edit, and delete any timesheet

## Installation

1. Copy this module to your Odoo addons directory
2. Update the apps list: Settings > Apps > Update Apps List
3. Search for "HR Timesheet - Read-only for Users"
4. Click "Install"

## Configuration

No configuration required. The module automatically applies the security restrictions upon installation.

## Technical Details

### Security Restrictions

The module overrides the default timesheet permissions through **Model Access Rights** (`security/hr_timesheet_security.xml`):

- Updates the existing access rules to remove write, create, and unlink permissions for standard timesheet users
- Maintains read-only access for viewing timesheets
- Uses `noupdate="0"` to ensure the security rules are properly updated
- Odoo automatically hides create/edit/delete buttons in the UI when users lack permissions

### User Groups Affected

- `hr_timesheet.group_hr_timesheet_user`: Standard users with restricted access
- `hr_timesheet.group_timesheet_manager`: Administrators with full access
- `hr_timesheet.group_hr_timesheet_approver`: Users who can view all timesheets (read-only unless they're also managers)

## Use Cases

This module is ideal for organizations where:
- Timesheet entries should be managed centrally by HR/Admin staff
- Users should not be able to modify their time tracking records
- Audit compliance requires preventing timesheet tampering

## Dependencies

- `hr_timesheet`: Core Odoo Timesheets module

## License

LGPL-3

## Author

Your Company
