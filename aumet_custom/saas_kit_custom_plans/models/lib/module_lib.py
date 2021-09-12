# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

import os
import logging


def check_if_module(addon_path, module_name):
    try:
        exists = False
        for path in addon_path:
            module_path = os.path.join(path, module_name)
            if os.path.isdir(module_path):
                if os.path.exists(os.path.join(module_path, '__manifest__.py')):
                    exists = True
                    break

        if exists:
            message = {
                'status': True,
                'msg': "Success, Module found"
            }
        else:
            message = {
                'status': False
            }
        return message
    except Exception as e:
        return {
        'status': False,
        'msg': e
    }