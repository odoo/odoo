# CAMTEL Audit Logging Module

Comprehensive audit logging system for CAMTEL warehouse operations.

## Features

### Authentication Tracking
- **Login Events**: Tracks successful user logins with IP address
- **Failed Login Attempts**: Records failed authentication attempts for security monitoring
- **Logout Events**: Monitors user logout activities

### Inventory Operations Tracking
- **Stock Pickings**: Logs creation, validation, and cancellation of stock transfers
- **Stock Moves**: Tracks product movements between locations
- **Inventory Adjustments**: Records inventory count adjustments

### Purchase Order Tracking
- **Order Creation**: Logs new purchase orders with supplier and amount details
- **Order Confirmation**: Tracks when orders are confirmed
- **Order Approval**: Records purchase order approvals (critical events)
- **Order Cancellation**: Monitors cancelled orders
- **Order Completion**: Logs completed purchase orders

### Security & Permissions Tracking
- **User Management**: Tracks user creation, modification, and deactivation
- **Group Changes**: Records security group modifications
- **Access Rights**: Logs changes to model-level access permissions
- **Record Rules**: Tracks row-level security rule modifications

## Installation

1. Copy the `camtel_audit` folder to your Odoo addons directory
2. Update your addons list:
   ```bash
   ./odoo-bin -d camtel_warehouse -u all
   ```
3. Install the module from Apps menu or via command line:
   ```bash
   ./odoo-bin -d camtel_warehouse -i camtel_audit
   ```

## Usage

### Viewing Audit Logs

Navigate to **Audit > Audit Logs** to view all logged events. The interface provides:

- **Tree View**: List of all audit events with color-coded severity levels
  - Red: Critical events (deletions, failed operations)
  - Orange: Warning events (approvals, permission changes)
  - Normal: Informational events

- **Filters**: Pre-configured filters for:
  - Time ranges (Today, Last 7 Days, Last 30 Days)
  - Event categories (Authentication, Inventory, Purchase, Security)
  - Event types (Login, Stock Operations, Purchase Orders, etc.)
  - Severity levels (Critical, Warning, Info)
  - Failed events

- **Group By**: Organize logs by:
  - Event Type
  - Category
  - User
  - Severity
  - Model
  - Date

### Reports

Access specialized reports under **Audit > Reports**:

- **Authentication Events**: All login/logout activities
- **Inventory Events**: Stock and warehouse operations
- **Purchase Events**: Purchase order activities
- **Security Events**: Permission and access modifications

### Analytics

Use the **Pivot** and **Graph** views to analyze:
- Event trends over time
- User activity patterns
- Most frequent operations
- Security event distribution

## Security

### User Roles

1. **Audit User** (`group_audit_user`)
   - Can view audit logs (read-only)
   - Cannot modify or delete logs

2. **Audit Manager** (`group_audit_manager`)
   - All Audit User permissions
   - Access to all reports and analytics

3. **System Administrators** (`base.group_system`)
   - Can create audit logs (automatic via system)
   - Cannot modify or delete existing logs

### Data Integrity

- **Immutable Logs**: Audit records cannot be modified or deleted
- **Automatic Logging**: All events are logged automatically via model inheritance
- **Fail-Safe**: Audit logging failures never interrupt business operations
- **Sudo Execution**: Logs are created with elevated privileges to ensure consistency

## Technical Details

### Models

- **camtel.audit.log**: Main audit log model
  - Stores all audit events
  - Includes event metadata, user info, resource references
  - Supports JSON storage for old/new values

### Inherited Models

The module extends the following Odoo models:

- `res.users`: Login/logout tracking, user management
- `stock.picking`: Stock transfer operations
- `stock.move`: Product movement tracking
- `purchase.order`: Purchase order lifecycle
- `res.groups`: Security group modifications
- `ir.model.access`: Access rights changes
- `ir.rule`: Record rule modifications

### API Usage

To manually create audit logs from custom code:

```python
self.env['camtel.audit.log'].create_log(
    event_type='other',
    description='Custom event description',
    model_name='your.model',
    res_id=record.id,
    resource_name=record.name,
    severity='info',  # 'info', 'warning', or 'critical'
    success=True,
    old_values={'field': 'old_value'},
    new_values={'field': 'new_value'},
    additional_data={'extra': 'data'}
)
```

## Dependencies

- `base`: Odoo base module
- `stock`: Inventory management
- `purchase`: Purchase management
- `web`: Web interface

## Version

- **Version**: 19.0.1.0.0
- **Odoo Version**: 19.0
- **License**: LGPL-3

## Support

For issues or questions, contact the CAMTEL development team.

## Compliance

This module is designed to meet audit and compliance requirements for:
- Warehouse operations tracking
- Financial transaction monitoring
- Security event logging
- User activity auditing
