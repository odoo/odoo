# # -*- coding: utf-8 -*-
# # Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
import sys

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests import common, tagged
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class BaseAutomationTest(TransactionCaseWithUserDemo):

    def setUp(self):
        super(BaseAutomationTest, self).setUp()
        self.user_root = self.env.ref('base.user_root')
        self.user_admin = self.env.ref('base.user_admin')

        self.test_mail_template_automation = self.env['mail.template'].create({
            'name': 'Template Automation',
            'model_id': self.env.ref('test_base_automation.model_base_automation_lead_test').id,
            'body_html': """&lt;div&gt;Email automation&lt;/div&gt;""",
        })

        self.res_partner_1 = self.env['res.partner'].create({'name': 'My Partner'})
        self.env['base.automation'].create([
            {
                'name': 'Base Automation: test rule on create',
                'model_id': self.env.ref('test_base_automation.model_base_automation_lead_test').id,
                'state': 'code',
                'code': "records.write({'user_id': %s})" % (self.user_demo.id),
                'trigger': 'on_create',
                'active': True,
                'filter_domain': "[('state', '=', 'draft')]",
            }, {
                'name': 'Base Automation: test rule on write',
                'model_id': self.env.ref('test_base_automation.model_base_automation_lead_test').id,
                'state': 'code',
                'code': "records.write({'user_id': %s})" % (self.user_demo.id),
                'trigger': 'on_write',
                'active': True,
                'filter_domain': "[('state', '=', 'done')]",
                'filter_pre_domain': "[('state', '=', 'open')]",
            }, {
                'name': 'Base Automation: test rule on recompute',
                'model_id': self.env.ref('test_base_automation.model_base_automation_lead_test').id,
                'state': 'code',
                'code': "records.write({'user_id': %s})" % (self.user_demo.id),
                'trigger': 'on_write',
                'active': True,
                'filter_domain': "[('employee', '=', True)]",
            }, {
                'name': 'Base Automation: test recursive rule',
                'model_id': self.env.ref('test_base_automation.model_base_automation_lead_test').id,
                'state': 'code',
                'code': """
record = model.browse(env.context['active_id'])
if 'partner_id' in env.context['old_values'][record.id]:
    record.write({'state': 'draft'})""",
                'trigger': 'on_write',
                'active': True,
            }, {
                'name': 'Base Automation: test rule on secondary model',
                'model_id': self.env.ref('test_base_automation.model_base_automation_line_test').id,
                'state': 'code',
                'code': "records.write({'user_id': %s})" % (self.user_demo.id),
                'trigger': 'on_create',
                'active': True,
            }, {
                'name': 'Base Automation: test rule on write check context',
                'model_id': self.env.ref('test_base_automation.model_base_automation_lead_test').id,
                'state': 'code',
                'code': """
record = model.browse(env.context['active_id'])
if 'user_id' in env.context['old_values'][record.id]:
    record.write({'is_assigned_to_admin': (record.user_id.id == 1)})""",
                'trigger': 'on_write',
                'active': True,
            }, {
                'name': 'Base Automation: test rule with trigger',
                'model_id': self.env.ref('test_base_automation.model_base_automation_lead_test').id,
                'trigger_field_ids': [(4, self.env.ref('test_base_automation.field_base_automation_lead_test__state').id)],
                'state': 'code',
                'code': """
record = model.browse(env.context['active_id'])
record['name'] = record.name + 'X'""",
                'trigger': 'on_write',
                'active': True,
            }, {
                'name': 'Base Automation: test send an email',
                'model_id': self.env.ref('test_base_automation.model_base_automation_lead_test').id,
                'template_id': self.test_mail_template_automation.id,
                'trigger_field_ids': [(4, self.env.ref('test_base_automation.field_base_automation_lead_test__deadline').id)],
                'state': 'email',
                'code': """
record = model.browse(env.context['active_id'])
record['name'] = record.name + 'X'""",
                'trigger': 'on_write',
                'active': True,
                'filter_domain': "[('deadline', '!=', False)]",
                'filter_pre_domain': "[('deadline', '=', False)]",
            }
        ])

    def tearDown(self):
        super().tearDown()
        self.env['base.automation']._unregister_hook()

    def create_lead(self, **kwargs):
        vals = {
            'name': "Lead Test",
            'user_id': self.user_root.id,
        }
        vals.update(kwargs)
        return self.env['base.automation.lead.test'].create(vals)

    def test_00_check_to_state_open_pre(self):
        """
        Check that a new record (with state = open) doesn't change its responsible
        when there is a precondition filter which check that the state is open.
        """
        lead = self.create_lead(state='open')
        self.assertEqual(lead.state, 'open')
        self.assertEqual(lead.user_id, self.user_root, "Responsible should not change on creation of Lead with state 'open'.")

    def test_01_check_to_state_draft_post(self):
        """
        Check that a new record changes its responsible when there is a postcondition
        filter which check that the state is draft.
        """
        lead = self.create_lead()
        self.assertEqual(lead.state, 'draft', "Lead state should be 'draft'")
        self.assertEqual(lead.user_id, self.user_demo, "Responsible should be change on creation of Lead with state 'draft'.")

    def test_02_check_from_draft_to_done_with_steps(self):
        """
        A new record is created and goes from states 'open' to 'done' via the
        other states (open, pending and cancel). We have a rule with:
         - precondition: the record is in "open"
         - postcondition: that the record is "done".
        If the state goes from 'open' to 'done' the responsible is changed.
        If those two conditions aren't verified, the responsible remains the same.
        """
        lead = self.create_lead(state='open')
        self.assertEqual(lead.state, 'open', "Lead state should be 'open'")
        self.assertEqual(lead.user_id, self.user_root, "Responsible should not change on creation of Lead with state 'open'.")
        # change state to pending and check that responsible has not changed
        lead.write({'state': 'pending'})
        self.assertEqual(lead.state, 'pending', "Lead state should be 'pending'")
        self.assertEqual(lead.user_id, self.user_root, "Responsible should not change on creation of Lead with state from 'draft' to 'open'.")
        # change state to done and check that responsible has not changed
        lead.write({'state': 'done'})
        self.assertEqual(lead.state, 'done', "Lead state should be 'done'")
        self.assertEqual(lead.user_id, self.user_root, "Responsible should not chang on creation of Lead with state from 'pending' to 'done'.")

    def test_03_check_from_draft_to_done_without_steps(self):
        """
        A new record is created and goes from states 'open' to 'done' via the
        other states (open, pending and cancel). We have a rule with:
         - precondition: the record is in "open"
         - postcondition: that the record is "done".
        If the state goes from 'open' to 'done' the responsible is changed.
        If those two conditions aren't verified, the responsible remains the same.
        """
        lead = self.create_lead(state='open')
        self.assertEqual(lead.state, 'open', "Lead state should be 'open'")
        self.assertEqual(lead.user_id, self.user_root, "Responsible should not change on creation of Lead with state 'open'.")
        # change state to done and check that responsible has changed
        lead.write({'state': 'done'})
        self.assertEqual(lead.state, 'done', "Lead state should be 'done'")
        self.assertEqual(lead.user_id, self.user_demo, "Responsible should be change on write of Lead with state from 'open' to 'done'.")

    def test_10_recomputed_field(self):
        """
        Check that a rule is executed whenever a field is recomputed after a
        change on another model.
        """
        partner = self.res_partner_1
        partner.write({'employee': False})
        lead = self.create_lead(state='open', partner_id=partner.id)
        self.assertFalse(lead.employee, "Customer field should updated to False")
        self.assertEqual(lead.user_id, self.user_root, "Responsible should not change on creation of Lead with state from 'draft' to 'open'.")
        # change partner, recompute on lead should trigger the rule
        partner.write({'employee': True})
        lead.flush()
        self.assertTrue(lead.employee, "Customer field should updated to True")
        self.assertEqual(lead.user_id, self.user_demo, "Responsible should be change on write of Lead when Customer becomes True.")

    def test_11_recomputed_field(self):
        """
        Check that a rule is executed whenever a field is recomputed and the
        context contains the target field
        """
        partner = self.res_partner_1
        lead = self.create_lead(state='draft', partner_id=partner.id)
        self.assertFalse(lead.deadline, 'There should not be a deadline defined')
        # change priority and user; this triggers deadline recomputation, and
        # the server action should set the boolean field to True
        lead.write({'priority': True, 'user_id': self.user_root.id})
        self.assertTrue(lead.deadline, 'Deadline should be defined')
        self.assertTrue(lead.is_assigned_to_admin, 'Lead should be assigned to admin')

    def test_11b_recomputed_field(self):
        mail_automation = self.env['base.automation'].search([('name', '=', 'Base Automation: test send an email')])
        send_mail_count = 0

        def _patched_get_actions(*args, **kwargs):
            obj = args[0]
            if '__action_done' not in obj._context:
                obj = obj.with_context(__action_done={})
            return mail_automation.with_env(obj.env)

        def _patched_send_mail(*args, **kwargs):
            nonlocal send_mail_count
            send_mail_count += 1

        patchers = [
            patch('odoo.addons.base_automation.models.base_automation.BaseAutomation._get_actions', _patched_get_actions),
            patch('odoo.addons.mail.models.mail_template.MailTemplate.send_mail', _patched_send_mail),
        ]

        patchers[0].start()

        lead = self.create_lead()
        self.assertFalse(lead.priority)
        self.assertFalse(lead.deadline)

        patchers[1].start()

        lead.write({'priority': True})

        self.assertTrue(lead.priority)
        self.assertTrue(lead.deadline)

        for patcher in patchers:
            patcher.stop()

        self.assertEqual(send_mail_count, 1)

    def test_12_recursive(self):
        """ Check that a rule is executed recursively by a secondary change. """
        lead = self.create_lead(state='open')
        self.assertEqual(lead.state, 'open')
        self.assertEqual(lead.user_id, self.user_root)
        # change partner; this should trigger the rule that modifies the state
        partner = self.res_partner_1
        lead.write({'partner_id': partner.id})
        self.assertEqual(lead.state, 'draft')

    def test_20_direct_line(self):
        """
        Check that a rule is executed after creating a line record.
        """
        line = self.env['base.automation.line.test'].create({'name': "Line"})
        self.assertEqual(line.user_id, self.user_demo)

    def test_20_indirect_line(self):
        """
        Check that creating a lead with a line executes rules on both records.
        """
        lead = self.create_lead(line_ids=[(0, 0, {'name': "Line"})])
        self.assertEqual(lead.state, 'draft', "Lead state should be 'draft'")
        self.assertEqual(lead.user_id, self.user_demo, "Responsible should change on creation of Lead test line.")
        self.assertEqual(len(lead.line_ids), 1, "New test line is not created")
        self.assertEqual(lead.line_ids.user_id, self.user_demo, "Responsible should be change on creation of Lead test line.")

    def test_21_trigger_fields(self):
        """
        Check that the rule with trigger is executed only once per pertinent update.
        """
        lead = self.create_lead(name="X")
        lead.priority = True
        partner1 = self.res_partner_1
        lead.partner_id = partner1.id
        self.assertEqual(lead.name, 'X', "No update until now.")

        lead.state = 'open'
        self.assertEqual(lead.name, 'XX', "One update should have happened.")
        lead.state = 'done'
        self.assertEqual(lead.name, 'XXX', "One update should have happened.")
        lead.state = 'done'
        self.assertEqual(lead.name, 'XXX', "No update should have happened.")
        lead.state = 'cancel'
        self.assertEqual(lead.name, 'XXXX', "One update should have happened.")

        # change the rule to trigger on partner_id
        rule = self.env['base.automation'].search([('name', '=', 'Base Automation: test rule with trigger')])
        rule.write({'trigger_field_ids':  [(6, 0, [self.env.ref('test_base_automation.field_base_automation_lead_test__partner_id').id])]})

        partner2 = self.env['res.partner'].create({'name': 'A new partner'})
        lead.name = 'X'
        lead.state = 'open'
        self.assertEqual(lead.name, 'X', "No update should have happened.")
        lead.partner_id = partner2
        self.assertEqual(lead.name, 'XX', "One update should have happened.")
        lead.partner_id = partner2
        self.assertEqual(lead.name, 'XX', "No update should have happened.")
        lead.partner_id = partner1
        self.assertEqual(lead.name, 'XXX', "One update should have happened.")

    def test_30_modelwithoutaccess(self):
        """
        Ensure a domain on a M2O without user access doesn't fail.
        We create a base automation with a filter on a model the user haven't access to
        - create a group
        - restrict acl to this group and set only admin in it
        - create base.automation with a filter
        - create a record in the restricted model in admin
        - create a record in the non restricted model in demo
        """
        Model = self.env['base.automation.link.test']
        Comodel = self.env['base.automation.linked.test']

        access = self.env.ref("test_base_automation.access_base_automation_linked_test")
        access.group_id = self.env['res.groups'].create({
            'name': "Access to base.automation.linked.test",
            "users": [(6, 0, [self.user_admin.id,])]
        })

        # sanity check: user demo has no access to the comodel of 'linked_id'
        with self.assertRaises(AccessError):
            Comodel.with_user(self.user_demo).check_access_rights('read')

        # check base automation with filter that performs Comodel.search()
        self.env['base.automation'].create({
            'name': 'test no access',
            'model_id': self.env['ir.model']._get_id("base.automation.link.test"),
            'trigger': 'on_create_or_write',
            'filter_pre_domain': "[('linked_id.another_field', '=', 'something')]",
            'state': 'code',
            'active': True,
            'code': "action = [rec.name for rec in records]"
        })
        Comodel.create([
            {'name': 'a first record', 'another_field': 'something'},
            {'name': 'another record', 'another_field': 'something different'},
        ])
        rec1 = Model.create({'name': 'a record'})
        rec1.write({'name': 'a first record'})
        rec2 = Model.with_user(self.user_demo).create({'name': 'another record'})
        rec2.write({'name': 'another value'})

        # check base automation with filter that performs Comodel.name_search()
        self.env['base.automation'].create({
            'name': 'test no name access',
            'model_id': self.env['ir.model']._get_id("base.automation.link.test"),
            'trigger': 'on_create_or_write',
            'filter_pre_domain': "[('linked_id', '=', 'whatever')]",
            'state': 'code',
            'active': True,
            'code': "action = [rec.name for rec in records]"
        })
        rec3 = Model.create({'name': 'a random record'})
        rec3.write({'name': 'a first record'})
        rec4 = Model.with_user(self.user_demo).create({'name': 'again another record'})
        rec4.write({'name': 'another value'})


@common.tagged('post_install', '-at_install')
class TestCompute(common.TransactionCase):
    def test_inversion(self):
        """ If a stored field B depends on A, an update to the trigger for A
        should trigger the recomputaton of A, then B.

        However if a search() is performed during the computation of A
        ??? and _order is affected ??? a flush will be triggered, forcing the
        computation of B, based on the previous A.

        This happens if a rule has has a non-empty filter_pre_domain, even if
        it's an empty list (``'[]'`` as opposed to ``False``).
        """
        company1 = self.env['res.partner'].create({
            'name': "Gorofy",
            'is_company': True,
        })
        company2 = self.env['res.partner'].create({
            'name': "Awiclo",
            'is_company': True
        })
        r = self.env['res.partner'].create({
            'name': 'Bob',
            'is_company': False,
            'parent_id': company1.id
        })
        self.assertEqual(r.display_name, 'Gorofy, Bob')
        r.parent_id = company2
        self.assertEqual(r.display_name, 'Awiclo, Bob')

        self.env['base.automation'].create({
            'name': "test rule",
            'filter_pre_domain': False,
            'trigger': 'on_create_or_write',
            'state': 'code', # no-op action
            'model_id': self.env.ref('base.model_res_partner').id,
        })
        r.parent_id = company1
        self.assertEqual(r.display_name, 'Gorofy, Bob')

        self.env['base.automation'].create({
            'name': "test rule",
            'filter_pre_domain': '[]',
            'trigger': 'on_create_or_write',
            'state': 'code', # no-op action
            'model_id': self.env.ref('base.model_res_partner').id,
        })
        r.parent_id = company2
        self.assertEqual(r.display_name, 'Awiclo, Bob')

    def test_recursion(self):
        project = self.env['test_base_automation.project'].create({})

        # this action is executed every time a task is assigned to project
        self.env['base.automation'].create({
            'name': 'dummy',
            'model_id': self.env['ir.model']._get_id('test_base_automation.task'),
            'state': 'code',
            'trigger': 'on_create_or_write',
            'filter_domain': repr([('project_id', '=', project.id)]),
        })

        # create one task in project with 10 subtasks; all the subtasks are
        # automatically assigned to project, too
        task = self.env['test_base_automation.task'].create({'project_id': project.id})
        subtasks = task.create([{'parent_id': task.id} for _ in range(10)])
        subtasks.flush()

        # This test checks what happens when a stored recursive computed field
        # is marked to compute on many records, and automated actions are
        # triggered depending on that field.  In this case, we trigger the
        # recomputation of 'project_id' on 'subtasks' by deleting their parent
        # task.
        #
        # An issue occurs when the domain of automated actions is evaluated by
        # method search(), because the latter flushes the fields to search on,
        # which are also the ones being recomputed.  Combined with the fact
        # that recursive fields are not computed in batch, this leads to a huge
        # amount of recursive calls between the automated action and flush().
        #
        # The execution of task.unlink() looks like this:
        # - mark 'project_id' to compute on subtasks
        # - delete task
        # - flush()
        #   - recompute 'project_id' on subtask1
        #     - call compute on subtask1
        #     - in action, search([('id', 'in', subtask1.ids), ('project_id', '=', pid)])
        #       - flush(['id', 'project_id'])
        #         - recompute 'project_id' on subtask2
        #           - call compute on subtask2
        #           - in action search([('id', 'in', subtask2.ids), ('project_id', '=', pid)])
        #             - flush(['id', 'project_id'])
        #               - recompute 'project_id' on subtask3
        #                 - call compute on subtask3
        #                 - in action, search([('id', 'in', subtask3.ids), ('project_id', '=', pid)])
        #                   - flush(['id', 'project_id'])
        #                     - recompute 'project_id' on subtask4
        #                       ...
        limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(100)
            task.unlink()
        finally:
            sys.setrecursionlimit(limit)
