# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
Demo Data for Base Automation Testing

This module creates example automations that showcase various trigger types and patterns.
All demos use test models (base.automation.lead.test, test_base_automation.project) to
avoid dependencies on business modules.

Usage:
    Install test_base_automation module with demo data enabled:
    odoo-bin -d your_db -i test_base_automation --load-language=en_US
"""

import logging

_logger = logging.getLogger(__name__)


def create_demo_time_based_automation(env):
    """
    Demo: Time-based trigger automation

    Pattern: Sends a reminder 3 days after lead creation
    Trigger: on_time (3 days after create_date)
    Model: base.automation.lead.test
    """
    _logger.info("Creating demo: Time-based lead reminder automation")

    Lead = env["base.automation.lead.test"]
    model_lead = env["ir.model"]._get("base.automation.lead.test")
    date_field = env["ir.model.fields"]._get("base.automation.lead.test", "create_date")

    # Create the automation
    automation = env["base.automation"].create(
        {
            "name": "Demo: Lead Follow-up Reminder (3 days)",
            "model_id": model_lead.id,
            "trigger": "on_time",
            "trg_date_id": date_field.id,
            "trg_date_range": 3,
            "trg_date_range_type": "day",
            "active": True,
        }
    )

    # Create the action
    env["ir.actions.server"].create(
        {
            "name": "Send Follow-up Reminder",
            "model_id": model_lead.id,
            "state": "code",
            "code": """
# This action runs 3 days after lead creation
log(f"Follow-up reminder for lead: {record.name}")
record.write({
    'user_id': env.user.id,
    'state': 'open',
})
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
        }
    )

    _logger.info(f"Created automation: {automation.name} (ID: {automation.id})")
    return automation


def create_demo_priority_escalation(env):
    """
    Demo: Field change trigger

    Pattern: Auto-assigns high priority leads to admin
    Trigger: on_write (when priority changes to '3')
    Model: base.automation.lead.test
    """
    _logger.info("Creating demo: Priority escalation automation")

    Lead = env["base.automation.lead.test"]
    model_lead = env["ir.model"]._get("base.automation.lead.test")
    priority_field = env["ir.model.fields"]._get(
        "base.automation.lead.test", "priority"
    )

    automation = env["base.automation"].create(
        {
            "name": "Demo: High Priority Lead Escalation",
            "model_id": model_lead.id,
            "trigger": "on_write",
            "filter_domain": "[('priority', '=', '3')]",
            "active": True,
        }
    )

    env["ir.actions.server"].create(
        {
            "name": "Escalate to Admin",
            "model_id": model_lead.id,
            "state": "code",
            "code": """
# Auto-assign high priority leads to admin
admin_user = env.ref('base.user_admin')
log(f"Escalating high priority lead: {record.name}")
record.write({
    'user_id': admin_user.id,
    'state': 'pending',
})
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
        }
    )

    _logger.info(f"Created automation: {automation.name} (ID: {automation.id})")
    return automation


def create_demo_state_transition(env):
    """
    Demo: State transition automation

    Pattern: Automatically moves leads through workflow states
    Trigger: on_write (when state changes to 'open')
    Model: base.automation.lead.test
    """
    _logger.info("Creating demo: State transition automation")

    model_lead = env["ir.model"]._get("base.automation.lead.test")
    state_field = env["ir.model.fields"]._get("base.automation.lead.test", "state")

    automation = env["base.automation"].create(
        {
            "name": "Demo: Auto-advance Open Leads",
            "model_id": model_lead.id,
            "trigger": "on_write",
            "filter_domain": "[('state', '=', 'open')]",
            "active": True,
        }
    )

    env["ir.actions.server"].create(
        {
            "name": "Advance to Pending",
            "model_id": model_lead.id,
            "state": "code",
            "code": """
# Automatically advance leads from open to pending after initial processing
if record.user_id:
    log(f"Auto-advancing lead: {record.name}")
    record.write({'state': 'pending'})
else:
    log(f"Cannot advance {record.name}: no user assigned")
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
        }
    )

    _logger.info(f"Created automation: {automation.name} (ID: {automation.id})")
    return automation


def create_demo_webhook_integration(env):
    """
    Demo: Webhook trigger

    Pattern: Accepts webhook payloads to create/update leads
    Trigger: on_webhook
    Model: base.automation.lead.test
    """
    _logger.info("Creating demo: Webhook integration automation")

    model_lead = env["ir.model"]._get("base.automation.lead.test")

    automation = env["base.automation"].create(
        {
            "name": "Demo: Webhook Lead Creation",
            "model_id": model_lead.id,
            "trigger": "on_webhook",
            "record_getter": """
# Find or create lead based on external ID
external_id = payload.get('external_id')
if not external_id:
    raise ValueError("Missing external_id in payload")

lead = model.search([('name', '=', external_id)], limit=1)
if not lead:
    lead = model.create({
        'name': external_id,
        'priority': str(payload.get('priority', '1')),
        'state': 'draft',
    })
    log(f"Created new lead from webhook: {external_id}")
else:
    log(f"Found existing lead: {external_id}")

lead
""",
            "active": True,
        }
    )

    env["ir.actions.server"].create(
        {
            "name": "Process Webhook Data",
            "model_id": model_lead.id,
            "state": "code",
            "code": """
# Update lead with webhook payload data
customer_name = payload.get('customer_name', 'Unknown Customer')
record.write({
    'customer_id': env['res.partner'].search([('name', '=', customer_name)], limit=1).id or False,
    'state': 'open',
})
log(f"Processed webhook for: {record.name}, Customer: {customer_name}")
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
        }
    )

    _logger.info(f"Created automation: {automation.name} (ID: {automation.id})")
    _logger.info(
        f"Webhook URL will be: /base_automation/webhook/{automation.webhook_uuid}"
    )
    return automation


def create_demo_multi_action_workflow(env):
    """
    Demo: Multi-action automation

    Pattern: Sequential actions on lead creation
    Trigger: on_create
    Model: base.automation.lead.test
    """
    _logger.info("Creating demo: Multi-action workflow automation")

    model_lead = env["ir.model"]._get("base.automation.lead.test")

    automation = env["base.automation"].create(
        {
            "name": "Demo: New Lead Onboarding Workflow",
            "model_id": model_lead.id,
            "trigger": "on_create",
            "active": True,
        }
    )

    # Action 1: Initialize lead
    env["ir.actions.server"].create(
        {
            "name": "Initialize Lead",
            "model_id": model_lead.id,
            "state": "code",
            "code": """
# Set initial state and priority
log(f"Initializing new lead: {record.name}")
record.write({
    'state': 'draft',
    'priority': '1',
})
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
            "sequence": 10,
        }
    )

    # Action 2: Assign to user
    env["ir.actions.server"].create(
        {
            "name": "Auto-assign Lead",
            "model_id": model_lead.id,
            "state": "code",
            "code": """
# Auto-assign to admin if no user set
if not record.user_id:
    admin_user = env.ref('base.user_admin')
    log(f"Auto-assigning lead {record.name} to {admin_user.name}")
    record.write({'user_id': admin_user.id})
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
            "sequence": 20,
        }
    )

    # Action 3: Log creation
    env["ir.actions.server"].create(
        {
            "name": "Log Lead Creation",
            "model_id": model_lead.id,
            "state": "code",
            "code": """
# Log lead creation event
log(f"Lead onboarding complete: {record.name}, User: {record.user_id.name if record.user_id else 'None'}")
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
            "sequence": 30,
        }
    )

    _logger.info(
        f"Created automation: {automation.name} (ID: {automation.id}) with 3 actions"
    )
    return automation


def create_demo_runtime_workflow(env):
    """
    Demo: Runtime workflow (DAG-based)

    Pattern: Multi-step approval workflow with dependencies
    Trigger: on_hand (manual runtime execution)
    Model: base.automation
    """
    _logger.info("Creating demo: Runtime workflow with DAG")

    model_automation = env["ir.model"]._get("base.automation")

    automation = env["base.automation"].create(
        {
            "name": "Demo: Multi-Step Approval Workflow",
            "model_id": model_automation.id,
            "trigger": "on_hand",
            "use_workflow_dag": True,
            "auto_execute_workflow": False,  # Manual step-by-step execution
            "active": True,
        }
    )

    # Step 1: Review
    action_review = env["ir.actions.server"].create(
        {
            "name": "Review Request",
            "model_id": model_automation.id,
            "state": "code",
            "code": """
# Step 1: Initial review
log(f"Reviewing request for: {runtime.partner_id.name if runtime.partner_id else 'No partner'}")
log(f"Amount: {runtime.amount if hasattr(runtime, 'amount') else 'N/A'}")
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
            "sequence": 10,
        }
    )

    # Step 2: Approval (depends on review)
    action_approve = env["ir.actions.server"].create(
        {
            "name": "Approve Request",
            "model_id": model_automation.id,
            "state": "code",
            "code": """
# Step 2: Approval
log(f"Request approved for: {runtime.partner_id.name if runtime.partner_id else 'No partner'}")
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
            "sequence": 20,
        }
    )
    action_approve.write({"predecessor_ids": [(6, 0, [action_review.id])]})

    # Step 3: Notification (depends on approval)
    action_notify = env["ir.actions.server"].create(
        {
            "name": "Send Notification",
            "model_id": model_automation.id,
            "state": "code",
            "code": """
# Step 3: Send notification
log(f"Notification sent for approved request: {runtime.partner_id.name if runtime.partner_id else 'No partner'}")
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
            "sequence": 30,
        }
    )
    action_notify.write({"predecessor_ids": [(6, 0, [action_approve.id])]})

    _logger.info(
        f"Created runtime workflow: {automation.name} (ID: {automation.id}) with 3-step DAG"
    )
    return automation


def create_demo_project_automation(env):
    """
    Demo: Automation on secondary test model

    Pattern: Project state management
    Trigger: on_write
    Model: test_base_automation.project
    """
    _logger.info("Creating demo: Project automation")

    model_project = env["ir.model"]._get("test_base_automation.project")

    automation = env["base.automation"].create(
        {
            "name": "Demo: Project Progress Tracker",
            "model_id": model_project.id,
            "trigger": "on_write",
            "filter_domain": "[('state', '=', 'in_progress')]",
            "active": True,
        }
    )

    env["ir.actions.server"].create(
        {
            "name": "Track Project Progress",
            "model_id": model_project.id,
            "state": "code",
            "code": """
# Track project progress
log(f"Project in progress: {record.name}")
if not record.user_id:
    admin_user = env.ref('base.user_admin')
    record.write({'user_id': admin_user.id})
    log(f"Auto-assigned project {record.name} to {admin_user.name}")
""",
            "base_automation_id": automation.id,
            "usage": "base_automation",
        }
    )

    _logger.info(f"Created automation: {automation.name} (ID: {automation.id})")
    return automation


def _setup_demo_data(env):
    """
    Main entry point for demo data creation.

    This function is called when the module is installed with demo data enabled.
    It creates all demo automations showcasing various patterns.
    """
    _logger.info("=" * 80)
    _logger.info("CREATING BASE AUTOMATION DEMO DATA")
    _logger.info("=" * 80)

    try:
        # Create all demo automations
        demo_automations = []

        demo_automations.append(create_demo_time_based_automation(env))
        demo_automations.append(create_demo_priority_escalation(env))
        demo_automations.append(create_demo_state_transition(env))
        demo_automations.append(create_demo_webhook_integration(env))
        demo_automations.append(create_demo_multi_action_workflow(env))
        demo_automations.append(create_demo_runtime_workflow(env))
        demo_automations.append(create_demo_project_automation(env))

        _logger.info("=" * 80)
        _logger.info(
            f"DEMO DATA CREATED SUCCESSFULLY: {len(demo_automations)} automations"
        )
        _logger.info("=" * 80)
        _logger.info("")
        _logger.info("Demo Automations:")
        for idx, automation in enumerate(demo_automations, 1):
            _logger.info(f"  {idx}. {automation.name} (Trigger: {automation.trigger})")
        _logger.info("")
        _logger.info(
            "Access automations: Settings > Technical > Automation > Automated Actions"
        )
        _logger.info("=" * 80)

    except Exception as e:
        _logger.error(f"Error creating demo data: {e}", exc_info=True)
        raise
