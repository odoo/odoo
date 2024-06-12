from . import models

import base64

from odoo.tools import file_open


def _setup_module(env):
    if env.ref('base.main_company', False): 
        with file_open('base/static/img/res_company_logo.png', 'rb') as file:
            env.ref('base.main_company').write({
                'appbar_image': base64.b64encode(file.read())
            })
            