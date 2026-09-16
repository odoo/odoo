# Copyright 2012 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo.addons.queue_job.exception import JobError, RetryableJobError

# Connector related errors


class ConnectorException(Exception):
    """Base Exception for the connectors"""


class NoConnectorUnitError(ConnectorException):
    """No ConnectorUnit has been found"""


class InvalidDataError(ConnectorException):
    """Data Invalid"""


# Job related errors


class MappingError(ConnectorException):
    """An error occurred during a mapping transformation."""


class NetworkRetryableError(RetryableJobError):
    """A network error caused the failure of the job, it can be retried later."""


class NoExternalId(RetryableJobError):
    """No External ID found, it can be retried later."""


class IDMissingInBackend(JobError):
    """The ID does not exist in the backend"""


class ManyIDSInBackend(JobError):
    """Unique key exists many times in backend"""
