# Attendance Project Timesheet Integration

## Overview

This module integrates employee attendance (check-in/check-out) with project management and automatic timesheet generation. When employees check in, timesheets are automatically created for the project they're working on. Employees can switch projects during the day, and each project change creates a new timesheet entry.

## Features

- **Automatic Timesheet Creation**: Timesheets are automatically created when an employee checks in
- **Project Tracking**: Each attendance record is linked to a project
- **Last Project Memory**: System remembers the last project each employee worked on
- **Project Switching**: Employees can change projects during their work day
- **Multiple Timesheets**: One attendance record can have multiple timesheet entries (one per project)
- **Default Project**: Fallback to "0 - Koszty Stałe" project for general overhead
- **Kiosk Mode Support**: Project selection available in kiosk mode
- **Web Interface**: Full project management in web interface

## Installation

1. Copy this module to your Odoo addons directory
2. Update the addons list: Settings → Apps → Update Apps List
3. Search for "Attendance Project Timesheet Integration"
4. Click Install

**Dependencies**: This module requires `hr_attendance`, `hr_timesheet`, and `project` modules.

## Configuration

### Default Project

The module automatically creates a default project "0 - Koszty Stałe" (Fixed Costs) during installation. This project is used when:
- Employee has no last project
- Employee has no default project set
- No project is specified during check-in

### Employee Settings

You can configure per-employee project settings:

1. Go to Employees → Employees
2. Open an employee record
3. Navigate to "HR Settings" tab
4. Set:
   - **Last Project**: Automatically updated when employee works on projects
   - **Default Project**: Fallback project for this employee

## Usage

### Check-In Workflow

1. **First Check-In** (no history):
   - Employee checks in
   - System uses default project "0 - Koszty Stałe"
   - Timesheet entry is created with 0 hours
   - Project is remembered for next time

2. **Subsequent Check-Ins**:
   - Employee checks in
   - System automatically uses last project employee worked on
   - Timesheet entry is created
   - Work continues on the same project

### Changing Projects During Work

**Method 1: Web Interface**
1. Open Attendances → My Attendances
2. Click on active attendance record
3. Click "Change Project" button
4. Select new project
5. Click "Change Project" to confirm
   - Current timesheet is closed (hours calculated)
   - New timesheet is created for new project
   - Active timesheet is updated

**Method 2: Kiosk Mode**
1. Employee checks in via kiosk
2. After check-in, kiosk shows current project
3. Click "Change Project" button
4. Select new project or check out
5. Confirm change

### Check-Out Workflow

1. Employee checks out
2. All active timesheets are closed
3. Hours are calculated based on time worked
4. Last project is saved for next check-in

### Multiple Projects in One Day

Example scenario:
- 08:00 - Check in → Project A starts
- 10:00 - Change to Project B → Project A closes (2 hours), Project B starts
- 14:00 - Change to Project C → Project B closes (4 hours), Project C starts
- 17:00 - Check out → Project C closes (3 hours)

Result: 3 timesheet entries for one attendance record:
- Project A: 2 hours
- Project B: 4 hours
- Project C: 3 hours

## Technical Details

### Models Extended

**hr.attendance**
- `project_id`: Current project for this attendance
- `timesheet_ids`: One2many link to generated timesheets
- `active_timesheet_id`: Currently active (not closed) timesheet
- `action_change_project()`: Opens wizard to change project
- `change_project_to(project_id)`: Executes project change

**hr.employee**
- `last_project_id`: Last project this employee worked on
- `default_project_id`: Default project for this employee

**account.analytic.line** (Timesheet)
- `attendance_id`: Link back to attendance record that created this timesheet

### New Models

**attendance.change.project.wizard**
- TransientModel wizard for changing projects
- Shows current project and allows selection of new project
- Provides "Check Out" option as alternative

### Automatic Calculations

Hours are automatically calculated based on:
- Check-in time
- Project change times
- Check-out time

Formula for each timesheet:
```
hours = (end_time - start_time) / 3600
```

Where:
- `start_time` = check_in OR time of previous project change
- `end_time` = check_out OR time of next project change OR now

## Troubleshooting

### Error: "No default project found"

**Solution**: Ensure the default project exists:
1. Go to Projects → Projects
2. Create project "0 - Koszty Stałe"
3. Enable "Timesheets" in project settings

### Timesheet hours are incorrect

**Cause**: Project was changed but timesheet not properly closed.

**Solution**:
1. Open the attendance record
2. Check the "Timesheets" tab
3. Manually adjust hours if needed
4. Or delete incorrect timesheet and check out/in again

### Cannot change project after check-out

**Expected Behavior**: Projects cannot be changed after check-out. This is by design to maintain timesheet integrity.

**Solution**: If you need to adjust:
1. Manually edit the timesheet entries in Timesheets → All Timesheets
2. Or delete the attendance record and recreate it

## Best Practices

1. **Check In Promptly**: Check in when you start work to ensure accurate time tracking
2. **Change Projects Immediately**: Switch projects as soon as you start working on something new
3. **Check Out Daily**: Always check out at end of day to close all timesheets
4. **Review Timesheets**: Periodically review your timesheets for accuracy
5. **Set Default Project**: Configure a default project for each employee to avoid using generic "Koszty Stałe"

## Support

For issues or questions:
1. Check this README
2. Review the CLAUDE.md file in the repository root
3. Contact your Odoo administrator

## License

LGPL-3

## Credits

Developed for Sage ERP
Odoo Version: 19.0
