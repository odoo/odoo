# Test Base Automation Module

## Overview

This module provides comprehensive testing infrastructure and demo examples for Odoo's **base_automation** module. It includes dedicated test models, extensive test suites, and practical automation examples that showcase various trigger types and workflow patterns.

**Key Features:**
- 🧪 **109+ integration tests** covering all automation functionality
- 📊 **Test models** designed specifically for automation testing
- 🎯 **Demo automations** showcasing real-world patterns
- 🔄 **No external dependencies** - fully self-contained
- 📝 **Comprehensive documentation** for learning and reference

---

## Purpose

The `test_base_automation` module serves three primary purposes:

1. **Testing Infrastructure**: Provides isolated test models that allow comprehensive testing of automation features without depending on business modules (sale, crm, etc.)

2. **Integration Testing**: Contains 109+ tests covering time triggers, webhooks, runtime workflows, DAG dependencies, and error handling

3. **Learning Resource**: Includes working demo automations that demonstrate best practices and common patterns for building automations

---

## Test Models

### 1. `base.automation.lead.test`
**Purpose:** Primary test model for automation testing

**Fields:**
- `name` (Char) - Lead name/identifier
- `user_id` (Many2one: res.users) - Assigned user
- `partner_id` (Many2one: res.partner) - Related partner (renamed from customer_id)
- `priority` (Selection: 1/2/3) - Priority level
- `state` (Selection: draft/open/pending/done/cancel) - Lead state
- `create_date` / `write_date` (Datetime) - Timestamps

**Use cases:**
- Time-based triggers (e.g., "3 days after creation")
- Field change triggers (e.g., priority escalation)
- State transition workflows
- Webhook integrations
- Multi-action workflows

### 2. `base.automation.lead.thread.test`
**Purpose:** Test model with mail.thread functionality

**Inherits:** `base.automation.lead.test` + `mail.thread`

**Additional features:**
- Message tracking
- Activity management
- Email integration

**Use cases:**
- Mail-based automations
- Activity scheduling
- Message posting automations

### 3. `test_base_automation.project`
**Purpose:** Secondary test model for multi-model scenarios

**Fields:**
- `name` (Char) - Project name
- `user_id` (Many2one: res.users) - Project manager
- `state` (Selection: draft/in_progress/done/cancel) - Project state

**Use cases:**
- Demonstrating automations work across different models
- Multi-model workflow testing
- Cross-model dependencies

---

## Test Coverage

### Test Suites (109+ Tests Total)

#### **test_flow.py** - Basic Automation Flow (27 tests)
- Trigger execution (on_create, on_write, on_unlink)
- Domain filtering
- Action execution
- Multi-action workflows
- Error handling

#### **test_time_triggers.py** - Time-Based Triggers (16 tests)
- on_time trigger with various intervals (minutes, hours, days, months)
- Date field calculations
- last_run tracking
- Cron job execution
- Multiple automations

#### **test_webhook_integration.py** - Webhooks (26 tests)
- UUID generation and rotation
- Webhook URL computation
- Payload processing (simple, _model/_id, custom fields)
- record_getter evaluation
- Error handling (invalid getter, no record, deleted record)
- Multi-action webhook workflows
- Logging

#### **test_runtime_workflows.py** - Runtime Workflows (18 tests)
- Runtime creation and lifecycle
- Progress tracking (0% → 100%)
- Next step execution
- Cancellation (idempotent)
- Context propagation (partner, amount, date, company)
- DAG dependency resolution (sequential, parallel)
- Error handling
- Edge cases (concurrent runtimes, single action)

#### **test_server_actions.py** - Server Actions (Integration tests)
- Action execution in automation context
- Code actions with automation variables
- Error propagation

#### **test_tour.py** - UI Tours (Integration tests)
- User interface workflows
- Automation creation via UI

---

## Demo Automations

Install the module with demo data to see these examples in action:

```bash
odoo-bin -d your_database -i test_base_automation --without-demo=False
```

### 1. Time-Based Lead Reminder
**Trigger:** 3 days after lead creation
**Pattern:** Automated follow-up reminders
**Model:** `base.automation.lead.test`

```python
# Sends reminder 3 days after lead is created
# Automatically assigns to admin and moves to "open" state
```

### 2. High Priority Lead Escalation
**Trigger:** When priority changes to "3" (High)
**Pattern:** Priority-based routing
**Model:** `base.automation.lead.test`

```python
# Automatically assigns high-priority leads to admin user
# Escalates state to "pending" for urgent action
```

### 3. Auto-Advance Open Leads
**Trigger:** When state changes to "open"
**Pattern:** State-based workflow progression
**Model:** `base.automation.lead.test`

```python
# Advances leads from "open" to "pending" if user assigned
# Logs progression for audit trail
```

### 4. Webhook Lead Creation
**Trigger:** Webhook POST request
**Pattern:** External system integration
**Model:** `base.automation.lead.test`

**Example webhook call:**
```bash
curl -X POST https://your-odoo.com/base_automation/webhook/UUID \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "EXT-12345",
    "customer_name": "Acme Corp",
    "priority": "2"
  }'
```

### 5. New Lead Onboarding Workflow
**Trigger:** On lead creation
**Pattern:** Multi-step initialization
**Model:** `base.automation.lead.test`

**Sequential actions:**
1. Initialize lead (set state, priority)
2. Auto-assign to user if not set
3. Log creation event

### 6. Multi-Step Approval Workflow (Runtime)
**Trigger:** Manual runtime execution
**Pattern:** DAG-based approval process
**Model:** `base.automation` (runtime)

**DAG structure:**
```
Review Request → Approve Request → Send Notification
```

### 7. Project Progress Tracker
**Trigger:** When project state = "in_progress"
**Pattern:** Project management automation
**Model:** `test_base_automation.project`

```python
# Tracks projects in progress
# Auto-assigns if no user set
```

---

## Running Tests

### Run All Tests
```bash
odoo-bin -d test_db -i test_base_automation --test-enable --stop-after-init
```

### Run Specific Test File
```bash
# Time triggers only
odoo-bin -d test_db -i test_base_automation --test-tags test_time_triggers --test-enable --stop-after-init

# Webhooks only
odoo-bin -d test_db -i test_base_automation --test-tags test_webhook_integration --test-enable --stop-after-init

# Runtime workflows only
odoo-bin -d test_db -i test_base_automation --test-tags test_runtime_workflows --test-enable --stop-after-init
```

### Run Specific Test Class
```bash
odoo-bin -d test_db -i test_base_automation --test-tags TestTimeBasedTriggers --test-enable --stop-after-init
```

---

## Automation Patterns & Best Practices

### Pattern 1: Time-Based Triggers

**Use case:** Send reminder X days/hours after record creation or update

```python
automation = env['base.automation'].create({
    'name': 'Follow-up Reminder',
    'model_id': model_lead.id,
    'trigger': 'on_time',
    'trg_date_id': create_date_field.id,
    'trg_date_range': 3,
    'trg_date_range_type': 'day',
})
```

**Key points:**
- Executes via cron job (hourly by default)
- Uses `last_run` to avoid duplicate executions
- Supports minutes, hours, days, months

### Pattern 2: Field Change Triggers

**Use case:** React to specific field value changes

```python
automation = env['base.automation'].create({
    'name': 'Priority Escalation',
    'model_id': model_lead.id,
    'trigger': 'on_write',
    'filter_domain': "[('priority', '=', '3')]",
})
```

**Key points:**
- Triggers only when domain matches
- Can check old vs new values
- Supports complex domain expressions

### Pattern 3: Webhook Integration

**Use case:** Accept data from external systems

```python
automation = env['base.automation'].create({
    'name': 'External Lead Creation',
    'model_id': model_lead.id,
    'trigger': 'on_webhook',
    'record_getter': """
external_id = payload.get('external_id')
lead = model.search([('name', '=', external_id)], limit=1)
if not lead:
    lead = model.create({'name': external_id})
lead
    """,
})
```

**Key points:**
- `record_getter` must return a recordset
- Access payload via `payload` variable
- Available variables: `model`, `env`, `payload`, `log`
- UUID-based webhook URL for security

### Pattern 4: Multi-Action Workflows

**Use case:** Execute multiple actions sequentially

```python
automation = env['base.automation'].create({
    'name': 'Onboarding Workflow',
    'model_id': model_lead.id,
    'trigger': 'on_create',
})

# Action 1
env['ir.actions.server'].create({
    'name': 'Initialize',
    'base_automation_id': automation.id,
    'sequence': 10,
    'code': "record.write({'state': 'draft'})",
})

# Action 2
env['ir.actions.server'].create({
    'name': 'Assign',
    'base_automation_id': automation.id,
    'sequence': 20,
    'code': "record.write({'user_id': env.user.id})",
})
```

**Key points:**
- Actions execute in sequence order
- All actions share same record context
- If one action fails, subsequent actions don't run

### Pattern 5: Runtime Workflows (DAG)

**Use case:** Manual multi-step workflows with dependencies

```python
automation = env['base.automation'].create({
    'name': 'Approval Workflow',
    'model_id': model_automation.id,
    'trigger': 'on_hand',
    'use_workflow_dag': True,
    'auto_execute_workflow': False,
})

# Create actions with dependencies
action1 = create_action('Review', automation)
action2 = create_action('Approve', automation)
action2.write({'predecessor_ids': [(6, 0, [action1.id])]})
```

**Key points:**
- Manual execution (`runtime.action_next_step()`)
- DAG ensures correct execution order
- Progress tracking (X/Y steps, percentage)
- Can store runtime context (partner, amount, date)

---

## Development Guide

### Creating Custom Test Models

Add new test models to `models/` directory:

```python
# models/my_test_model.py
from odoo import models, fields

class MyTestModel(models.Model):
    _name = 'my.test.model'
    _description = 'My Test Model'

    name = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ])
```

### Adding New Tests

Create test files in `tests/` directory following naming convention:

```python
# tests/test_my_feature.py
from odoo.tests import TransactionCase, tagged

@tagged('post_install', '-at_install', 'test_my_feature')
class TestMyFeature(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Model = self.env['my.test.model']

    def test_something(self):
        """Test description."""
        record = self.Model.create({'name': 'Test'})
        self.assertEqual(record.state, 'draft')
```

### Creating Demo Automations

Add demo functions to `demo/demo_data.py`:

```python
def create_demo_my_automation(env):
    """Demo: My Custom Automation"""
    _logger.info("Creating demo: My automation")

    automation = env['base.automation'].create({
        'name': 'Demo: My Automation',
        # ... configuration
    })

    return automation

# Register in _setup_demo_data():
def _setup_demo_data(env):
    demo_automations = []
    demo_automations.append(create_demo_my_automation(env))
    # ...
```

---

## Troubleshooting

### Tests Not Running

**Issue:** Tests don't execute when running with `--test-enable`

**Solution:**
```bash
# Ensure test_base_automation is installed
odoo-bin -d test_db -i test_base_automation --test-enable --stop-after-init

# Or upgrade if already installed
odoo-bin -d test_db -u test_base_automation --test-enable --stop-after-init
```

### Demo Data Not Created

**Issue:** Demo automations don't appear after installation

**Solution:**
```bash
# Install with demo data enabled
odoo-bin -d test_db -i test_base_automation --without-demo=False --stop-after-init

# Check module was installed with demo
# Settings > Technical > Modules > Search "test_base_automation"
# Verify "Demo Data" checkbox is checked
```

### Webhook URL Not Working

**Issue:** Webhook returns 404 or errors

**Solution:**
1. Verify automation has `trigger = 'on_webhook'`
2. Check webhook UUID was generated: `automation.webhook_uuid`
3. Use correct URL format: `/base_automation/webhook/{UUID}`
4. Ensure record_getter returns a recordset

### Time Trigger Not Executing

**Issue:** Time-based automation doesn't run at expected time

**Solution:**
1. Check cron job is active: **Settings > Technical > Scheduled Actions > "Trigger time-based automations"**
2. Verify `last_run` field to see when it last executed
3. Ensure record meets time criteria (e.g., created 3 days ago)
4. Check filter_domain if specified

---

## Module Structure

```
test_base_automation/
├── __init__.py                 # Module initialization + post_init_hook
├── __manifest__.py             # Module metadata
├── README.md                   # This file
├── models/
│   ├── __init__.py
│   ├── base_automation_lead_test.py     # Primary test model
│   └── test_base_automation_project.py  # Secondary test model
├── security/
│   └── ir.model.access.csv     # Access rights
├── tests/
│   ├── __init__.py
│   ├── test_flow.py            # 27 tests - Basic automation flow
│   ├── test_server_actions.py  # Server action integration
│   ├── test_tour.py            # UI tours
│   ├── test_time_triggers.py   # 16 tests - Time-based triggers
│   ├── test_webhook_integration.py  # 26 tests - Webhooks
│   └── test_runtime_workflows.py    # 18 tests - Runtime workflows
└── demo/
    ├── __init__.py
    └── demo_data.py            # 7 demo automations
```

---

## API Reference

### Test Models

#### `base.automation.lead.test`
```python
env['base.automation.lead.test'].create({
    'name': 'Test Lead',
    'user_id': env.user.id,
    'partner_id': partner.id,
    'priority': '2',
    'state': 'draft',
})
```

#### `base.automation.lead.thread.test`
```python
env['base.automation.lead.thread.test'].create({
    'name': 'Threaded Lead',
    # ... same as lead.test
})
# Additional mail.thread features:
lead.message_post(body="Comment")
```

#### `test_base_automation.project`
```python
env['test_base_automation.project'].create({
    'name': 'Test Project',
    'user_id': env.user.id,
    'state': 'draft',
})
```

### Automation Context Variables

When writing automation code (in `ir.actions.server`), these variables are available:

- `env` - Odoo environment
- `model` - Current model (recordset class)
- `record` / `records` - Record(s) being processed
- `runtime` - Runtime workflow instance (for on_hand trigger)
- `payload` - Webhook payload (for on_webhook trigger)
- `log()` - Logging function
- `Warning` - Odoo warning exception

**Example:**
```python
# In server action code field:
log(f"Processing {record.name}")
if record.priority == '3':
    record.write({'user_id': env.ref('base.user_admin').id})
    log(f"Escalated to admin")
```

---

## Version History

- **v1.0** (2025-01-20): Initial release with 109+ tests and 7 demo automations

---

## Contributing

This module is part of Odoo core testing infrastructure. Contributions should:

1. Add tests to appropriate test files
2. Follow existing test patterns (TransactionCase, tagged decorators)
3. Use test models (avoid production models)
4. Include docstrings explaining test purpose
5. Update this README if adding new patterns

---

## License

LGPL-3 (Odoo Standard License)

---

## Support

For issues or questions:
- Review test files for examples: `addons/test_base_automation/tests/`
- Check demo automations: `addons/test_base_automation/demo/demo_data.py`
- Consult base_automation documentation
- Run tests with `-v` flag for verbose output

---

## Credits

**Author:** Odoo S.A.
**Maintainer:** Odoo Core Team
**Category:** Hidden/Testing
**Module:** test_base_automation
