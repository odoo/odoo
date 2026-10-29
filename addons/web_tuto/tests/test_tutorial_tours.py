import contextlib
from unittest.mock import patch

from odoo import Command
from odoo.tests import HttpCase, loaded_demo_data, tagged

TYPED_VALUES = {
    'char': 'Tutorial',
    'text': 'Tutorial',
    'integer': '10',
    'float': '10',
    'monetary': '10',
}


@tagged('post_install', '-at_install')
class TestTutorialTours(HttpCase):
    """ Go through each tutorial of the database as a user would, step by step,
    with the "Next" button of its pointer, typing a value in its fields: a tour
    is built from the tutorial and saved with its steps, to be played as an
    automatic tour """

    def test_tutorials(self):
        if loaded_demo_data(self.env):
            self.skipTest("Onboarding tours are meant to run on a database without demo data")
        admin = self.env.ref('base.user_admin')
        admin.tutorial_tips_shown = True
        Tutorial = self.env['web_tuto.tutorial'].with_user(admin)
        tutorials = Tutorial.search([('chapter_ids', '!=', False)]).filtered(lambda t: t._is_accessible())
        for tutorial in tutorials:
            with self.subTest(tutorial=tutorial.name), contextlib.closing(self.env.cr.savepoint()):
                (tutorials - tutorial).mark_done()
                action_id = tutorial.action_restart()['params']['action_id']
                tour = self.env['web_tour.tour'].create({
                    'name': f'{tutorial.name}_test',
                    'step_ids': [
                        Command.create({'sequence': sequence, **tour_step})
                        for sequence, tour_step in enumerate(self._get_tour_steps(tutorial))
                    ],
                })
                with patch.object(self.registry['web_tuto.tutorial'], '_can_run', lambda self: True):
                    self.start_tour(f'/odoo/action-{action_id}', tour.name, login='admin')

    def _get_tour_steps(self, tutorial):
        """ The steps of the tour going through the tutorial, until its rainbow
        man, discarding the record it may leave unsaved """
        tutorial_steps = [
            (chapter, step)
            for chapter in tutorial._get_tutorial_json()['chapters']
            for step in chapter['steps']
        ]
        tour_steps = []
        stage_count = 0
        for index, (chapter, step) in enumerate(tutorial_steps, 1):
            tour_steps.append({
                'content': f"Wait for step {index}",
                'trigger': f'.o_tutorial_progress:contains("Step {index}/{len(tutorial_steps)}")',
            })
            if step['type'] == 'button' and step['name'] == 'create':
                stage_count += 1
                tour_steps += [
                    {
                        'content': "Open the stage creation",
                        'trigger': '.o_quick_create_folded .o_quick_create_button, .o_quick_create_unfolded input',
                        'run': 'click',
                    },
                    {
                        'content': "Name the stage",
                        'trigger': '.o_quick_create_unfolded input',
                        'run': f'edit Stage {stage_count}',
                    },
                    {
                        'content': "Add the stage",
                        'trigger': '.o_quick_create_unfolded .o_kanban_add',
                        'run': 'click',
                    },
                ]
                continue
            tour_steps.append({'content': f"Do step {index}", 'trigger': '.o_tutorial_next', 'run': 'click'})
            if step['type'] == 'field':
                tour_steps += self._get_field_tour_steps(chapter, step)
        return tour_steps + [
            {'content': "Finish the tutorial", 'trigger': '.o_reward_rainbow_man'},
            {
                'content': "Discard the record left unsaved",
                'trigger': '.o_form_button_cancel, body:not(:has(.o_form_dirty))',
                'run': 'click',
            },
            {'content': "Wait for the record to be discarded", 'trigger': 'body:not(:has(.o_form_dirty))'},
        ]

    def _get_field_tour_steps(self, chapter, step):
        """ The steps of the tour typing a value in the field of the step once
        focused by the "Next" button (the one of a one2many field adding a
        line): in a char, text or number field, or the name of a record of a
        many2one or many2many field (picked in its autocomplete, the user
        playing the tour for a field of users, as their domain may exclude
        the others), unless its widget isn't an input """
        Model = self.env[chapter['model']]
        if step.get('x2many'):
            Model = self.env[Model._fields[step['x2many']].comodel_name]
        field = Model._fields[step['name']]
        widget = self._get_widget(step)
        if field.type in ('many2one', 'many2many'):
            if widget and 'many2one' not in widget and 'many2many' not in widget:
                return []
            if field.comodel_name == 'res.users':
                value = self.env.ref('base.user_admin').display_name
            else:
                value = self.env[field.comodel_name].search([], limit=1).display_name or 'Tutorial'
        else:
            value = TYPED_VALUES.get(field.type)
        if value is None or widget in ('statusbar', 'priority'):
            return []
        if step.get('x2many'):
            selector = (
                f"{step['scope']} .o_field_widget[name='{step['x2many']}'] "
                f".o_data_row [name='{field.name}']"
            )
        else:
            selector = f"{step['scope']} .o_field_widget[name='{field.name}']"
        tour_steps = [{
            'content': f"Fill {field.name}",
            'trigger': f'{selector} input, {selector} textarea',
            'run': f'edit {value}',
        }]
        if field.type in ('many2one', 'many2many'):
            tour_steps.append({
                'content': f"Pick {value}",
                'trigger': (
                    f'{selector} .o-autocomplete--dropdown-item:not(.o_m2o_start_typing)'
                    f':not(.o_m2o_dropdown_option_create_edit, .o_m2o_dropdown_option_search_more)'
                    f':not(:has(.o_loading)):contains("{value}"):first'
                ),
                'run': 'click',
            })
        return tour_steps

    def _get_widget(self, step):
        """ The widget of the field of the step in the arch it was found in """
        chapter = self.env['web_tuto.step'].browse(step['id']).chapter_id
        arch = next(arch for arch, scope in chapter._get_archs() if scope == step['scope'])
        if step.get('x2many'):
            nodes = arch.xpath(
                '//field[@name=$parent][not(ancestor::field)]//field[@name=$name]',
                parent=step['x2many'], name=step['name'],
            )
        else:
            nodes = arch.xpath('//field[@name=$name][not(ancestor::field)]', name=step['name'])
        return nodes[0].get('widget') if nodes else None
