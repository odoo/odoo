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

It defines a single master thread that will spawn (a bounded number of)
threads to process individual cron jobs.

The thread runs forever, checking every 60 seconds for new
'database wake-ups'. It maintains a heapq of database wake-ups. At each
wake-up, it will call ir_cron._run_jobs_multithread() for the given database. _run_jobs_multithread
will check the jobs defined in the ir_cron table and spawn accordingly threads
to process them.

This module's behavior depends on the following configuration variable:
openerp.conf.max_cron_threads.

"""

import heapq
import logging
import threading
import time

import openerp
import tools

_logger = logging.getLogger(__name__)

# TODO: perhaps in the future we could consider a flag on ir.cron jobs
# that would cause database wake-up even if the database has not been
# loaded yet or was already unloaded (e.g. 'force_db_wakeup' or something)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
