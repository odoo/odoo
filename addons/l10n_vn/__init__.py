# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# This module is Copyright (c) 2009-2013 General Solutions (http://gscom.vn) All Rights Reserved.


def _post_init_hook(env):
    env.ref('l10n_vn.vn_template').process_coa_translations()
