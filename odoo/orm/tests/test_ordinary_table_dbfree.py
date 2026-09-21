"""A model backed by a view is not an ordinary table, on this tier too.

The live registry asks `pg_class` for `relkind = 'r'`. There is no catalog
here, and the stub answered True for everything -- so a model that has no
table of its own read as one, and the callers that refuse to act on such a
model never refused.
"""

import pytest

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.orm.model_test_env import model_test_env
from odoo.orm.runtime._backend_memory import _foreign_key_targets

_MOD = "test_ordinary_table_dbfree"


class Report(models.Model):
    _name = "ordinary.report"
    _module = _MOD
    _description = "a model its module backs with a SQL view"
    _auto = False
    _log_access = False

    name = fields.Char()


class Host(models.Model):
    _name = "ordinary.host"
    _module = _MOD
    _description = "a host referencing both kinds"
    _log_access = False

    name = fields.Char()
    report_id = fields.Many2one("ordinary.report")
    peer_id = fields.Many2one("ordinary.host")


@pytest.fixture
def env():
    with model_test_env(Report, Host, check_cache=False) as env:
        yield env


def test_a_view_backed_model_is_not_an_ordinary_table(env):
    assert not env["ordinary.report"]._is_an_ordinary_table()


def test_an_auto_model_is_an_ordinary_table(env):
    assert env["ordinary.host"]._is_an_ordinary_table()


def test_an_abstract_model_is_not_an_ordinary_table(env):
    assert not env["base"]._is_an_ordinary_table()


def test_exporting_the_id_of_a_view_backed_model_is_refused(env):
    # the caller that makes this visible: it refuses rather than inventing an
    # external id for a row no table owns
    with pytest.raises(UserError, match="not an ordinary table"):
        list(env["ordinary.report"].browse(1)._get_or_create_xml_ids())


def test_a_foreign_key_is_not_declared_against_a_view(env):
    # `update_db_foreign_key` declines the same pair, so neither tier has a
    # constraint to enforce here
    targets = dict(_foreign_key_targets(env["ordinary.host"]))
    assert "report_id" not in targets
    assert targets["peer_id"] == env["ordinary.host"]._table


def test_a_view_backed_model_declares_no_foreign_key_of_its_own(env):
    assert _foreign_key_targets(env["ordinary.report"]) == []
