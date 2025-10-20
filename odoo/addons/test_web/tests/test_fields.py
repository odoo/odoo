from odoo.tests import Form, tagged

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


@tagged('at_install', '-post_install')  # LEGACY at_install
class test_shared_cache(TransactionCaseWithUserDemo):
    def test_shared_cache_computed_field(self):
        # Test case: Check that the shared cache is not used if a compute_sudo stored field
        # is computed IF there is an ir.rule defined on this specific model.

        # Real life example:
        # A user can only see its own timesheets on a task, but the field "Planned Hours",
        # which is stored-compute_sudo, should take all the timesheet lines into account
        # However, when adding a new line and then recomputing the value, no existing line
        # from another user is binded on self, then the value is erased and saved on the
        # database.

        task = self.env['test_orm.model_shared_cache_compute_parent'].create({
            'name': 'Shared Task'})
        self.env['test_orm.model_shared_cache_compute_line'].create({
            'user_id': self.env.ref('base.user_admin').id,
            'parent_id': task.id,
            'amount': 1,
        })
        self.assertEqual(task.total_amount, 1)

        self.env.flush_all()
        self.env.invalidate_all()  # Start fresh, as it would be the case on 2 different sessions.

        task = task.with_user(self.user_demo)
        with Form(task) as task_form:
            # Use demo has no access to the already existing line
            self.assertEqual(len(task_form.line_ids), 0)
            # But see the real total_amount
            self.assertEqual(task_form.total_amount, 1)
            # Now let's add a new line (and retrigger the compute method)
            with task_form.line_ids.new() as line:
                line.amount = 2
            # The new value for total_amount, should be 3, not 2.
            self.assertEqual(task_form.total_amount, 2)
