from urllib3.util.ssl_ import create_urllib3_context

from odoo.libs import netguard
from odoo.libs.guarded_http import GuardedAdapter

from .structured_reference import *


class LegacyHTTPAdapter(GuardedAdapter):
    def __init__(self, *, policy=netguard.PUBLIC_ONLY, **kwargs):
        super().__init__(policy, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        OP_LEGACY_SERVER_CONNECT = 0x04
        context = create_urllib3_context(options=OP_LEGACY_SERVER_CONNECT)
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)
