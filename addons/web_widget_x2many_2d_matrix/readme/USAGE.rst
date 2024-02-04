Use this widget by saying::

<field name="my_field" widget="x2many_2d_matrix" />

This assumes that my_field refers to a model with the fields `x`, `y` and
`value`. If your fields are named differently, pass the correct names as
attributes:

.. code-block:: xml

    <field name="my_field" widget="x2many_2d_matrix" field_x_axis="my_field1" field_y_axis="my_field2" field_value="my_field3">
        <tree>
            <field name="my_field"/>
            <field name="my_field1"/>
            <field name="my_field2"/>
            <field name="my_field3"/>
        </tree>
    </field>

You can pass the following parameters:

field_x_axis
    The field that indicates the x value of a point
field_y_axis
    The field that indicates the y value of a point
field_value
    Show this field as value
show_row_totals
    If field_value is a numeric field, it indicates if you want to calculate
    row totals. True by default
show_column_totals
    If field_value is a numeric field, it indicates if you want to calculate
    column totals. True by default

Example
~~~~~~~

You need a data structure already filled with values. Let's assume we want to
use this widget in a wizard that lets the user fill in planned hours for one
task per project per user. In this case, we can use ``project.task`` as our
data model and point to it from our wizard. The crucial part is that we fill
the field in the default function:

.. code-block:: python

    from odoo import fields, models

    class MyWizard(models.TransientModel):
        _name = 'my.wizard'

        def _default_task_ids(self):
            # your list of project should come from the context, some selection
            # in a previous wizard or wherever else
            projects = self.env['project.project'].browse([1, 2, 3])
            # same with users
            users = self.env['res.users'].browse([1, 2, 3])
            return [
                (0, 0, {
                    'name': 'Sample task name',
                    'project_id': p.id,
                    'user_id': u.id,
                    'planned_hours': 0,
                    'message_needaction': False,
                    'date_deadline': fields.Date.today(),
                })
                # if the project doesn't have a task for the user,
                # create a new one
                if not p.task_ids.filtered(lambda x: x.user_id == u) else
                # otherwise, return the task
                (4, p.task_ids.filtered(lambda x: x.user_id == u)[0].id)
                for p in projects
                for u in users
            ]

        task_ids = fields.Many2many('project.task', default=_default_task_ids)

Now in our wizard, we can use:

.. code-block:: xml

    <field name="task_ids" widget="x2many_2d_matrix" field_x_axis="project_id" field_y_axis="user_id" field_value="planned_hours">
        <tree>
            <field name="task_ids"/>
            <field name="project_id"/>
            <field name="user_id"/>
            <field name="planned_hours"/>
        </tree>
    </field>
