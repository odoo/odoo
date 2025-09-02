import odoo.tests

class TestTour(odoo.tests.HttpCase):

    def test_example_of_tour1(self):
        stage = self.env['project.task.type'].create({'name': 'To Do'})
        project = self.env['project.project'].create([{
            'name': 'Project 1',
            'type_ids': stage.ids,
        }])

        self.env['project.task'].create({
            'name': 'Task 1',
            'stage_id': stage.id,
            'project_id': project.id,
        })

        self.start_tour('/odoo/project', 'example_of_tour1', login='admin', debug=1)
