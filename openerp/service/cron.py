#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

""" Cron jobs scheduling

Cron jobs are defined in the ir_cron table/model. This module deals with all
cron jobs, for all databases of a single OpenERP server instance.

"""

import logging
import threading
import time

import openerp

_logger = logging.getLogger(__name__)

SLEEP_INTERVAL = 60 # 1 min

def cron_runner(number):
    while True:
        time.sleep(SLEEP_INTERVAL + number) # Steve Reich timing style
        registries = openerp.modules.registry.RegistryManager.registries
        _logger.debug('cron%d polling for jobs', number)
        for db_name, registry in registries.items():
            while True and registry.ready:
                # acquired = openerp.addons.base.ir.ir_cron.ir_cron._acquire_job(db_name)
                # TODO why isnt openerp.addons.base defined ?
                import sys
                base = sys.modules['addons.base']
                acquired = base.ir.ir_cron.ir_cron._acquire_job(db_name)
                if not acquired:
                    break

def start_service():
    """ Start the above runner function in a daemon thread.

    The thread is a typical daemon thread: it will never quit and must be
    terminated when the main process exits - with no consequence (the processing
    threads it spawns are not marked daemon).

    """
    for i in range(openerp.tools.config['max_cron_threads']):
        def target():
            cron_runner(i)
        t = threading.Thread(target=target, name="openerp.service.cron.cron%d" % i)
        t.setDaemon(True)
        t.start()
        _logger.debug("cron%d started!" % i)

def stop_service():
    pass

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
