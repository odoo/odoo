# Copyright 2013 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import hashlib
import logging
import struct

_logger = logging.getLogger(__name__)


def pg_try_advisory_lock(env, lock):
    """Try to acquire a Postgres transactional advisory lock.

    The function tries to acquire a lock, returns a boolean indicating
    if it could be obtained or not. An acquired lock is released at the
    end of the transaction.

    A typical use is to acquire a lock at the beginning of an importer
    to prevent 2 jobs to do the same import at the same time. Since the
    record doesn't exist yet, we can't put a lock on a record, so we put
    an advisory lock.

    Example:
     - Job 1 imports Partner A
     - Job 2 imports Partner B
     - Partner A has a category X which happens not to exist yet
     - Partner B has a category X which happens not to exist yet
     - Job 1 import category X as a dependency
     - Job 2 import category X as a dependency

    Since both jobs are executed concurrently, they both create a record
    for category X so we have duplicated records.  With this lock:

     - Job 1 imports Partner A, it acquires a lock for this partner
     - Job 2 imports Partner B, it acquires a lock for this partner
     - Partner A has a category X which happens not to exist yet
     - Partner B has a category X which happens not to exist yet
     - Job 1 import category X as a dependency, it acquires a lock for
       this category
     - Job 2 import category X as a dependency, try to acquire a lock
       but can't, Job 2 is retried later, and when it is retried, it
       sees the category X created by Job 1.

    The lock is acquired until the end of the transaction.

    Usage example:

    ::

        lock_name = 'import_record({}, {}, {}, {})'.format(
            self.backend_record._name,
            self.backend_record.id,
            self.model._name,
            self.external_id,
        )
        if pg_try_advisory_lock(lock_name):
            # do sync
        else:
            raise RetryableJobError('Could not acquire advisory lock',
                                    seconds=2,
                                    ignore_retry=True)

    :param env: the Odoo Environment
    :param lock: The lock name. Can be anything convertible to a
       string.  It needs to represents what should not be synchronized
       concurrently so usually the string will contain at least: the
       action, the backend type, the backend id, the model name, the
       external id
    :return True/False whether lock was acquired.
    """
    hasher = hashlib.sha1(str(lock).encode())
    # pg_lock accepts an int8 so we build an hash composed with
    # contextual information and we throw away some bits
    int_lock = struct.unpack("q", hasher.digest()[:8])

    env.cr.execute("SELECT pg_try_advisory_xact_lock(%s);", (int_lock,))
    acquired = env.cr.fetchone()[0]
    return acquired
