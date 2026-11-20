import logging
import time

from passlib.totp import TOTP

from odoo import http
from odoo.addons.auth_totp.controllers.home import Home
from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.tests import tagged

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestTOTPortal(HttpCaseWithUserPortal):
    """
    Largely replicates TestTOTP
    """
    def test_totp(self):
        totp = None
        # test endpoint as doing totp on the client side is not really an option
        # (needs sha1 and hmac + BE packing of 64b integers)
        def totp_hook(self, secret=None):
            nonlocal totp
            if totp is None:
                totp = TOTP(secret)
            if secret:
                return totp.generate().token
            else:
                # on check, take advantage of window because previous token has been
                # "burned" so we can't generate the same, but tour is so fast
                # we're pretty certainly within the same 30s
                return totp.generate(time.time() + 30).token
        # because not preprocessed by ControllerType metaclass
        totp_hook.routing_type = 'json'
        # patch Home to add test endpoint
        Home.totp_hook = http.route('/totphook', type='json', auth='none')(totp_hook)
        self.env.registry.clear_cache('routing')
        # remove endpoint and destroy routing map
        @self.addCleanup
        def _cleanup():
            del Home.totp_hook
            self.env.registry.clear_cache('routing')

        self.start_tour('/my/security', 'totportal_tour_setup', login='portal')
        # also disables totp otherwise we can't re-login
        self.start_tour('/', 'totportal_login_enabled', login=None)
        self.start_tour('/', 'totportal_login_disabled', login=None)
