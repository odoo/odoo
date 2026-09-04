# Copyright 2018 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import logging

import psycopg2

from odoo.addons.component.core import Component

from ..exception import RetryableJobError

_logger = logging.getLogger(__name__)


class RecordLocker(Component):
    """Component allowing to lock record(s) for the current transaction

    Example of usage::

        self.component('record.locker').lock(self.records)

    See the definition of :meth:`~lock` for details.
    """

    _name = "base.record.locker"
    _inherit = ["base.connector"]
    _usage = "record.locker"

    def lock(self, records, seconds=None, ignore_retry=True):
        """Lock the records.

        Lock the record so we are sure that only one job is running for this
        record(s) if concurrent jobs have to run a job for the same record(s).
        When concurrent jobs try to work on the same record(s), the first one
        will lock and proceed, the others will fail to acquire it and will be
        retried later
        (:exc:`~odoo.addons.queue_job.exception.RetryableJobError` is raised).

        The lock is using a ``FOR UPDATE NOWAIT`` so any concurrent transaction
        trying FOR UPDATE/UPDATE will be rejected until the current transaction
        is committed or rollbacked.

        A classical use case for this is to prevent concurrent exports.

        The following parameters are forwarded to the exception
        :exc:`~odoo.addons.queue_job.exception.RetryableJobError`

        :param seconds: In case of retry because the lock cannot be acquired,
                        in how many seconds it must be retried. If not set,
                        the queue_job configuration is used.
        :param ignore_retry: If True, the retry counter of the job will not be
                             increased.
        """
        sql = "SELECT id FROM %s WHERE ID IN %%s FOR UPDATE NOWAIT" % self.model._table
        try:
            self.env.cr.execute(sql, (tuple(records.ids),), log_exceptions=False)
        except psycopg2.OperationalError as err:
            _logger.info(
                "A concurrent job is already working on the same "
                "record (%s with one id in %s). Job delayed later.",
                self.model._name,
                tuple(records.ids),
            )
            raise RetryableJobError(
                "A concurrent job is already working on the same record "
                "(%s with one id in %s). The job will be retried later."
                % (self.model._name, tuple(records.ids)),
                seconds=seconds,
                ignore_retry=ignore_retry,
            ) from err
