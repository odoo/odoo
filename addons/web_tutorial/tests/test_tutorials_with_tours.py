import contextlib
from unittest.mock import patch

from lxml import etree, html

from odoo.fields import Command
from odoo.tests import HttpCase, loaded_demo_data, tagged

INVALID = ".o_tutorial_invalid"
NOT_INVALID = f"body:not(:has({INVALID}))"


def contains(text):
    """ Return the ``:contains`` pseudo-class matching the text """
    return ':contains("%s")' % text.replace('\\', '\\\\').replace('"', '\\"')


@tagged('post_install', '-at_install')
class TestTutorialsWithTours(HttpCase):
    """ Go through each tutorial of the database as a user would, step by
    step, with the "Next" button of its pointer, typing a value in its
    fields: a tour is made of its steps, and played from its action """

    def test_tutorials(self):
        if loaded_demo_data(self.env):
            self.skipTest("Tutorials are meant to run on a database without demo data")
        tutorials = self.env['web_tutorial.tutorial'].search([])
        if not tutorials:
            self.skipTest("No installed app has a tutorial")
        for tutorial in tutorials:
            with self.subTest(tutorial=tutorial.title), contextlib.closing(self.env.cr.savepoint()):
                self._start_tutorial_tour(tutorial)

    def _start_tutorial_tour(self, tutorial):
        """ Play the tutorial from its action, the other ones being done not
        to run meanwhile """
        admin = self.env.ref('base.user_admin')
        tutorial.expand_messages = True
        Tutorial = self.env['web_tutorial.tutorial'].with_user(admin)
        tutorial = tutorial.with_user(admin)
        (Tutorial.search([]) - tutorial).mark_done()
        action_id = tutorial.action_restart()['params']['action_id']
        tour = self.env['web_tour.tour'].create({
            'name': f'web_tutorial_{tutorial.id}_test',
            'custom': True,
            'step_ids': [
                Command.create({**step, 'sequence': sequence})
                for sequence, step in enumerate(self._get_tour_steps(tutorial))
            ],
        })
        with patch.object(self.registry['web_tutorial.tutorial'], '_can_run', lambda self: True):
            self.start_tour(f'/odoo/action-{action_id}', tour.name, login='admin')

    def _get_tour_steps(self, tutorial):
        """ Return the steps of the tour going through the tutorial, only
        through its pointer: for each step, wait for its bubble showing its
        help (the first text of its message), click "Next", and type a value
        in the field it focused, until its rainbow man; then close the dialog
        and discard the record it may leave open """
        steps = tutorial.step_ids
        tour_steps = []
        for index, step in enumerate(steps, 1):
            progress = f".o_tutorial_progress{contains(f'Step {index}/{len(steps)}')}"
            help_ = contains(self._get_help_text(step.message))
            tour_steps += [
                {'content': f"Wait for step {index}", 'trigger': f"{progress}, {INVALID}"},
                {'content': f"Step {index} isn't blocked by a field left invalid", 'trigger': NOT_INVALID},
                {
                    'content': f"Step {index} shows its help: {self._get_help_text(step.message)}",
                    'trigger': f".o_tutorial_pointer_content:has({progress}){help_}",
                },
                {'content': f"Do step {index}", 'trigger': ".o_tutorial_next", 'run': "click"},
            ]
            if step.type == 'field':
                tour_steps += self._get_fill_steps(step, progress)
        return [
            *tour_steps,
            {'content': "Wait for the end of the tutorial", 'trigger': f".o_reward_rainbow_man, {INVALID}"},
            {'content': "The end isn't blocked by a field left invalid", 'trigger': NOT_INVALID},
            {
                'content': "Close the dialog left open (e.g. confirming a deletion)",
                'trigger': ".modal .btn-close, body:not(:has(.modal))",
                'run': "click",
            },
            {
                'content': "Discard the record left unsaved",
                'trigger': ".o_form_button_cancel, body:not(:has(.o_form_dirty))",
                'run': "click",
            },
            {'content': "Wait for the record to be discarded", 'trigger': "body:not(:has(.o_form_dirty))"},
        ]

    def _get_help_text(self, message):
        """ Return the first text of the HTML message, before any other tag
        (e.g. "Welcome to" of "<h3>Welcome to <b>Project</b></h3>"), if any
        (none for an image alone) """
        return next((text.strip() for text in html.fromstring(message).itertext() if text.strip()), "")

    def _get_fill_steps(self, step, progress):
        """ Return the steps typing a value in the input of the field step
        "Next" focused, depending on the type of the field: a number, a text,
        or a record picked in the autocomplete of a relational field (created
        if none); none for the other fields (e.g. a date, stars, a statusbar,
        a x2many field adding a line) """
        model = self.env[step.res_model]
        x2many, _dot, name = step.name.rpartition('.')
        if x2many:
            model = self.env[model._fields[x2many].comodel_name]
            widget = ''
        else:
            widget = self._get_widget(model, name)
        field = model._fields[name]
        input_ = f"[name='{name}'] :is(input, textarea):focus"
        wait = {'content': f"Wait for the field {step.name} to be focused", 'trigger': f"body:not(:has({progress}))"}
        if field.type in ('integer', 'float', 'monetary'):
            return [wait, {'content': f"Fill {step.name}", 'trigger': input_, 'run': "edit 10"}]
        if field.type in ('char', 'text'):
            return [wait, {'content': f"Fill {step.name}", 'trigger': input_, 'run': "edit Tutorial"}]
        is_autocomplete = field.type == 'many2one' or (field.type == 'many2many' and widget)
        if not is_autocomplete or 'statusbar' in widget:
            return []
        menu = ".o-autocomplete--dropdown-menu:not(:has(.o_loading))"
        if self.env[field.comodel_name].search_count([], limit=1):
            return [
                wait,
                {'content': f"Open the records of {step.name}", 'trigger': input_, 'run': "click"},
                {
                    'content': f"Pick a record for {step.name}",
                    'trigger': f"{menu} .o-autocomplete--dropdown-item:not(.o_m2o_dropdown_option) a",
                    'run': "click",
                },
            ]
        return [
            wait,
            {'content': f"Type a new record for {step.name}", 'trigger': input_, 'run': "edit Tutorial"},
            {'content': f"Create it for {step.name}", 'trigger': f"{menu} .o_m2o_dropdown_option_create a", 'run': "click"},
        ]

    def _get_widget(self, model, name):
        """ Return the widget of the field in the form of the model, if any """
        arch = etree.fromstring(model.get_view(view_type='form')['arch'])
        node = next(iter(arch.xpath(f"//field[@name='{name}'][not(ancestor::field)]")), None)
        return node.get('widget', '') if node is not None else ''
