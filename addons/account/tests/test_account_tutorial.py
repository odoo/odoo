from requests import PreparedRequest, Response, Session

from odoo.tests import tagged

from odoo.addons.web_tutorial.tests.common import TutorialTourCase


@tagged('post_install', '-at_install')
class TestAccountTutorial(TutorialTourCase):

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        """ The tutorial opens the accounting dashboard, which fetches the
        bank institutions from odoofin """
        if 'proxy/v2/get_dashboard_institutions' in r.url:
            r = Response()
            r.status_code = 200
            r.json = list
            return r
        return super()._request_handler(s, r, **kw)

    def test_account_tutorial(self):
        self.start_tutorial_tour('account_tutorial')
