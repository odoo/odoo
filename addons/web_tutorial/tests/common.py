from unittest.mock import patch

from odoo.tests import HttpCase, loaded_demo_data

TOUR_MODULE = 'odoo.loader.modules.get("@web_tutorial/../tests/tours/tutorial_tours")'


class TutorialTourCase(HttpCase):
    """ Go through a tutorial as a user would, step by step, with the "Next"
    button of its pointer, typing a value in its fields: its tour
    ``<name>_test`` is registered for the test from its chapters in the
    registry ``web_tutorial.tutorials`` (see ``registerTutorialTour``) """

    def start_tutorial_tour(self, name):
        """ Play the tutorial from its action, the other ones being done not
        to run meanwhile

        :param name: the name of the tutorial
        """
        if loaded_demo_data(self.env):
            self.skipTest("Tutorials are meant to run on a database without demo data")
        admin = self.env.ref('base.user_admin')
        admin.tutorial_tips_shown = True
        Tutorial = self.env['web_tutorial.tutorial'].with_user(admin)
        tutorial = Tutorial.search([('name', '=', name)])
        (Tutorial.search([]) - tutorial).mark_done()
        action_id = tutorial.action_restart()['params']['action_id']
        with patch.object(self.registry['web_tutorial.tutorial'], '_can_run', lambda self: True):
            tour = f'{name}_test'
            self.start_tour(
                f'/odoo/action-{action_id}', tour, login='admin',
                ready=f"Boolean(odoo.isTourReady && {TOUR_MODULE})",
                code=f"{TOUR_MODULE}.registerTutorialTour({name!r}); odoo.startTour({tour!r})",
            )
