# -*- coding: utf-8 -*-
from openerp.addons.connector.exception import RetryableJobError


class OrderImportRuleRetry(RetryableJobError):
    """ The sale order import will be retried later. """
