# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

def _set_fiscal_country(env):
    """ Sets the fiscal country on existing companies when installing the module.
    That field is an editable computed field. It doesn't automatically get computed
    on existing records by the ORM when installing the module, so doing that by hand
    ensures existing records will get a value for it if needed.
    """
    env['res.company'].search([]).compute_account_tax_fiscal_country()


def _create_batch_payment_sequence(env):
    """ Creates a Batch Payment Number Sequence for every company that does not
    have one yet. This covers companies that existed before the ``account``
    module was installed.
    """
    to_create_seqs = env['res.company'].search([('batch_payment_sequence_id', '=', False)])
    to_create_seqs._create_batch_payment_sequence()


def _account_post_init(env):
    _set_fiscal_country(env)
    _create_batch_payment_sequence(env)

# imported here to avoid dependency cycle issues
# pylint: disable=wrong-import-position
from . import controllers
from . import models
from . import demo
from . import wizard
from . import report
from . import tools
