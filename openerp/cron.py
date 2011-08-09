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
wake-up, it will call ir_cron._run_jobs() for the given database. _run_jobs
will check the jobs defined in the ir_cron table and spawn accordingly threads
to process them.

This module behavior depends on the following configuration variable:
openerp.conf.max_cron_threads.

"""

import heapq
import logging
import threading
import time

import openerp

# Heapq of database wake-ups. Note that 'database wake-up' meaning is in
# the context of the cron management. This is not about loading a database
# or otherwise making anything about it.
# Each element is a triple (timestamp, database-name, boolean). The boolean
# specifies if the wake-up is canceled (so a wake-up can be canceled without
# relying on the heapq implementation detail; no need to remove the job from
# the heapq).
_wakeups = []

# Mapping of database names to the wake-up defined in the heapq,
# so that we can cancel the wake-up without messing with the heapq
# internal structure: lookup the wake-up by database-name, then set
# its third element to True.
_wakeup_by_db = {}

# Re-entrant lock to protect the above _wakeups and _wakeup_by_db variables.
# We could use a simple (non-reentrant) lock if the runner function below
# was more fine-grained, but we are fine with the loop owning the lock
# while spawning a few threads.
_wakeups_lock = threading.RLock()

# Maximum number of threads allowed to process cron jobs concurrently. This
# variable is set by start_master_thread using openerp.conf.max_cron_threads.
_thread_count = None

# A (non re-entrant) lock to protect the above _thread_count variable.
_thread_count_lock = threading.Lock()

_logger = logging.getLogger('cron')


def get_thread_count():
    """ Return the number of available threads. """
    return _thread_count


def inc_thread_count():
    """ Increment by the number of available threads. """
    global _thread_count
    with _thread_count_lock:
        _thread_count += 1


def dec_thread_count():
    """ Decrement by the number of available threads. """
    global _thread_count
    with _thread_count_lock:
        _thread_count -= 1


def cancel(db_name):
    """ Cancel the next wake-up of a given database, if any.

    :param db_name: database name for which the wake-up is canceled.

    """
    _logger.debug("Cancel next wake-up for database '%s'.", db_name)
    with _wakeups_lock:
        if db_name in _wakeup_by_db:
            _wakeup_by_db[db_name][2] = True


def cancel_all():
    """ Cancel all database wake-ups. """
    global _wakeups
    global _wakeup_by_db
    with _wakeups_lock:
        _wakeups = []
        _wakeup_by_db = {}


def schedule_in_advance(timestamp, db_name):
    """ Schedule a new wake-up for a database.

    If an earlier wake-up is already defined, the new wake-up is discarded.
    If another wake-up is defined, that wake-up is discarded and the new one
    is scheduled.

    :param db_name: database name for which a new wake-up is scheduled.
    :param timestamp: when the wake-up is scheduled.

    """
    if not timestamp:
        return
    with _wakeups_lock:
        # Cancel the previous wake-up if any.
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
        runner_body()

def runner_body():
    with _wakeups_lock:
        while _wakeups and _wakeups[0][0] < time.time() and get_thread_count():
            task = heapq.heappop(_wakeups)
            timestamp, db_name, canceled = task
            if canceled:
                continue
            task[2] = True
            registry = openerp.pooler.get_pool(db_name)
            if not registry._init:
                registry['ir.cron']._run_jobs()
    amount = 60
    with _wakeups_lock:
        # Sleep less than 60s if the next known wake-up will happen before.
        if _wakeups and get_thread_count():
            amount = min(60, _wakeups[0][0] - time.time())
    time.sleep(amount)


def start_master_thread():
    """ Start the above runner function in a daemon thread.

    The thread is a typical daemon thread: it will never quit and must be
    terminated when the main process exits - with no consequence (the processing
    threads it spawns are not marked daemon).

    """
    global _thread_count
    _thread_count = openerp.conf.max_cron_threads
    t = threading.Thread(target=runner, name="openerp.cron.master_thread")
    t.setDaemon(True)
    t.start()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
