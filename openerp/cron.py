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

# Heapq of database wake-ups. Note that 'database wake-up' meaning is in
# the context of the cron management. This is not originally about loading
# a database, although having the database name in the queue will
# cause it to be loaded when the schedule time is reached, even if it was
# unloaded in the mean time. Normally a database's wake-up is cancelled by
# the RegistryManager when the database is unloaded - so this should not
# cause it to be reloaded.
#
# TODO: perhaps in the future we could consider a flag on ir.cron jobs
# that would cause database wake-up even if the database has not been
# loaded yet or was already unloaded (e.g. 'force_db_wakeup' or something)
#
# Each element is a triple (timestamp, database-name, boolean). The boolean
# specifies if the wake-up is canceled (so a wake-up can be canceled without
# relying on the heapq implementation detail; no need to remove the job from
# the heapq).
_wakeups = []

# Mapping of database names to the wake-up defined in the heapq,
# so that we can cancel the wake-up without messing with the heapq
# invariant: lookup the wake-up by database-name, then set
# its third element to True.
_wakeup_by_db = {}

# Re-entrant lock to protect the above _wakeups and _wakeup_by_db variables.
# We could use a simple (non-reentrant) lock if the runner function below
# was more fine-grained, but we are fine with the loop owning the lock
# while spawning a few threads.
_wakeups_lock = threading.RLock()

# Maximum number of threads allowed to process cron jobs concurrently. This
# variable is set by start_master_thread using openerp.conf.max_cron_threads.
_thread_slots = None

# A (non re-entrant) lock to protect the above _thread_slots variable.
_thread_slots_lock = threading.Lock()

# Sleep duration limits - must not loop too quickly, but can't sleep too long
# either, because a new job might be inserted in ir_cron with a much sooner
# execution date than current known ones. We won't see it until we wake!
MAX_SLEEP = 60 # 1 min
MIN_SLEEP = 1  # 1 sec

# Dummy wake-up timestamp that can be used to force a database wake-up asap
WAKE_UP_NOW = 1

def get_thread_slots():
    """ Return the number of available thread slots """
    return _thread_slots


def release_thread_slot():
    """ Increment the number of available thread slots """
    global _thread_slots
    with _thread_slots_lock:
        _thread_slots += 1


def take_thread_slot():
    """ Decrement the number of available thread slots """
    global _thread_slots
    with _thread_slots_lock:
        _thread_slots -= 1


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
    _logger.debug("Cancel all database wake-ups")
    global _wakeups
    global _wakeup_by_db
    with _wakeups_lock:
        _wakeups = []
        _wakeup_by_db = {}


def schedule_wakeup(timestamp, db_name):
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
        if db_name in _wakeup_by_db:
            task = _wakeup_by_db[db_name]
            if not task[2] and timestamp > task[0]:
                # existing wakeup is valid and occurs earlier than new one
                return
            task[2] = True # cancel existing task
        task = [timestamp, db_name, False]
        heapq.heappush(_wakeups, task)
        _wakeup_by_db[db_name] = task
        _logger.debug("Wake-up scheduled for database '%s' @ %s", db_name,
                      'NOW' if timestamp == WAKE_UP_NOW else timestamp)

def runner():
    """Neverending function (intended to be run in a dedicated thread) that
       checks every 60 seconds the next database wake-up. TODO: make configurable
    """
    while True:
        runner_body()

def runner_body():
    with _wakeups_lock:
        while _wakeups and _wakeups[0][0] < time.time() and get_thread_slots():
            task = heapq.heappop(_wakeups)
            timestamp, db_name, canceled = task
            if canceled:
                continue
            del _wakeup_by_db[db_name]
            registry = openerp.pooler.get_pool(db_name)
            if not registry._init:
                _logger.debug("Database '%s' wake-up! Firing multi-threaded cron job processing", db_name)
                registry['ir.cron']._run_jobs_multithread()
    amount = MAX_SLEEP
    with _wakeups_lock:
        # Sleep less than MAX_SLEEP if the next known wake-up will happen before that.
        if _wakeups and get_thread_slots():
            amount = min(MAX_SLEEP, max(MIN_SLEEP, _wakeups[0][0] - time.time()))
    _logger.debug("Going to sleep for %ss", amount)
    time.sleep(amount)

def start_master_thread():
    """ Start the above runner function in a daemon thread.

    The thread is a typical daemon thread: it will never quit and must be
    terminated when the main process exits - with no consequence (the processing
    threads it spawns are not marked daemon).

    """
    global _thread_slots
    _thread_slots = openerp.conf.max_cron_threads
    db_maxconn = tools.config['db_maxconn']
    if _thread_slots >= tools.config.get('db_maxconn', 64):
        _logger.warning("Connection pool size (%s) is set lower than max number of cron threads (%s), "
                        "this may cause trouble if you reach that number of parallel cron tasks.",
                        db_maxconn, _thread_slots)
    t = threading.Thread(target=runner, name="openerp.cron.master_thread")
    t.setDaemon(True)
    t.start()
    _logger.debug("Master cron daemon started!")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
