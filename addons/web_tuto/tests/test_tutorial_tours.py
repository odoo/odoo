import contextlib
from unittest.mock import patch

from requests import PreparedRequest, Response, Session

from odoo.tests import HttpCase, loaded_demo_data, tagged

TOUR_MODULE = 'odoo.loader.modules.get("@web_tuto/../tests/tours/tutorial_tours")'


@tagged('post_install', '-at_install')
class TestTutorialTours(HttpCase):
    """ Go through each tutorial of the database as a user would, step by step,
    with the "Next" button of its pointer, typing a value in its fields: its
    tour ``<name>_test`` is registered for the test from its chapters in the
    registry ``web_tuto.tutorials`` (see ``registerTutorialTour``) """

    def test_tutorials(self):
        if loaded_demo_data(self.env):
            self.skipTest("Onboarding tours are meant to run on a database without demo data")
        admin = self.env.ref('base.user_admin')
        admin.tutorial_tips_shown = True
        Tutorial = self.env['web_tuto.tutorial'].with_user(admin)
        tutorials = Tutorial.search([]).filtered(lambda t: t._is_accessible())
        for tutorial in tutorials:
            with self.subTest(tutorial=tutorial.name), contextlib.closing(self.env.cr.savepoint()):
                (tutorials - tutorial).mark_done()
                action_id = tutorial.action_restart()['params']['action_id']
                with patch.object(self.registry['web_tuto.tutorial'], '_can_run', lambda self: True):
                    tour = f'{tutorial.name}_test'
                    self.start_tour(
                        f'/odoo/action-{action_id}', tour, login='admin',
                        ready=f"Boolean(odoo.isTourReady && {TOUR_MODULE})",
                        code=f"{TOUR_MODULE}.registerTutorialTour({tutorial.name!r}); odoo.startTour({tour!r})",
                    )

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        """ The tutorial of Invoicing opens the accounting dashboard, which
        fetches the bank institutions from odoofin """
        if 'proxy/v2/get_dashboard_institutions' in r.url:
            r = Response()
            r.status_code = 200
            r.json = list
            return r
        return super()._request_handler(s, r, **kw)
