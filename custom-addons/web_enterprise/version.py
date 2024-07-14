# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

# ----------------------------------------------------------
# Monkey patch release to set the edition as 'enterprise'
# ----------------------------------------------------------
odoo.release.version_info = odoo.release.version_info[:5] + ('e',)
if '+e' not in odoo.release.version:     # not already patched by packaging
    odoo.release.version = '{0}+e{1}{2}'.format(*odoo.release.version.partition('-'))

odoo.service.common.RPC_VERSION_1.update(
    server_version=odoo.release.version,
    server_version_info=odoo.release.version_info)
