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

"""

import heapq
import logging
import threading
import time

import openerp

""" Singleton that keeps track of cancellable tasks to run at a given
    timestamp.
   
    The tasks are characterised by:
   
        * a timestamp
        * the database on which the task run
        * a boolean attribute specifying if the task is canceled

    Implementation details:
    
      - Tasks are stored as list, allowing the cancellation by setting
        the boolean to True.
      - A heapq is used to store tasks, so we don't need to sort
        tasks ourself.
"""

# Heapq of database wake-ups. Note that 'database wake-up' meaning is in
# the context of the cron management. This is not about loading a database
# or otherwise making anything about it.
_wakeups = [] # TODO protect this variable with a lock?

# Mapping of database names to the wake-up defined in the heapq,
# so that we can cancel the wake-up without messing with the heapq
# internal structure.
_wakeup_by_db = {}

_logger = logging.getLogger('cron')

_thread_count_lock = threading.Lock()

# Maximum number of threads allowed to process cron jobs concurrently.
_thread_count = 2


def get_thread_count():
    return _thread_count


def inc_thread_count():
    global _thread_count
    with _thread_count_lock:
        _thread_count += 1


def dec_thread_count():
    global _thread_count
    with _thread_count_lock:
        _thread_count -= 1


def cancel(db_name):
    """ Cancel the next wake-up of a given database, if any. """
    _logger.debug("Cancel next wake-up for database '%s'.", db_name)
    if db_name in _wakeup_by_db:
        _wakeup_by_db[db_name][2] = True


def cancel_all():
    """ Cancel all database wake-ups. """
    global _wakeups
    global _wakeup_by_db
    _wakeups = []
    _wakeup_by_db = {}


def schedule_in_advance(timestamp, db_name):
    """ Schedule a wake-up for a new database.

    If an earlier wake-up is already defined, the new wake-up is discarded.
    If another wake-up is defined, it is discarded.

    """
    if not timestamp:
        return
    # Cancel the previous wakeup if any.
    add_wakeup = False
    if db_name in _wakeup_by_db:
        task = _wakeup_by_db[db_name]
        if task[2] or timestamp < task[0]:
            add_wakeup = True
            task[2] = True
    else:
        add_wakeup = True
    if add_wakeup:
        task = [timestamp, db_name, False]
        heapq.heappush(_wakeups, task)
        _wakeup_by_db[db_name] = task


def runner():
    """Neverending function (intended to be ran in a dedicated thread) that
       checks every 60 seconds the next database wake-up. TODO: make configurable
    """
    while True:
        while _wakeups and _wakeups[0][0] < time.time() and get_thread_count():
            task = heapq.heappop(_wakeups)
            timestamp, db_name, canceled = task
            if canceled:
                continue
            task[2] = True
            registry = openerp.pooler.get_pool(db_name)
            if not registry._init:
                registry['ir.cron']._run_jobs()
        if _wakeups and get_thread_count():
            time.sleep(min(60, _wakeups[0][0] - time.time()))
        else:
            time.sleep(60)


def start_master_thread():
    """ Start the above runner function in a daemon thread.

    The thread is a typical daemon thread: it will never quit and must be
    terminated when the main process exits - with no consequence (the processing
    threads it spawns are not marked daemon).

    """
    t = threading.Thread(target=runner, name="openerp.cron.master_thread")
    t.setDaemon(True)
    t.start()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
