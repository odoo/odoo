import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_xmlids_port_dbfree"


class Thing(models.Model):
    _name = "xp.thing"
    _module = _MOD
    _description = "a record an external id may name"
    _log_access = False

    name = fields.Char()


class IrModelData(models.Model):
    _name = "ir.model.data"
    _module = _MOD
    _description = "ir.model.data (xmlid port stub)"
    _log_access = False

    module = fields.Char()
    name = fields.Char()
    model = fields.Char()
    res_id = fields.Integer()
    noupdate = fields.Boolean()

    def _xmlid_to_res_model_res_id(self, xmlid, raise_if_not_found=False):
        module, _dot, name = xmlid.partition(".")
        data = self.search([("module", "=", module), ("name", "=", name)], limit=1)
        if data:
            return data.model, data.res_id
        if raise_if_not_found:
            raise ValueError(f"External ID not found in the system: {xmlid}")
        return (False, False)


def test_ref_goes_through_the_registry_port(monkeypatch):
    with model_test_env(Thing) as env:
        asked = []

        def target(_port, _env, xml_id, raise_if_not_found):
            asked.append((xml_id, raise_if_not_found))
            return (False, False)

        monkeypatch.setattr(type(env.registry.xmlids), "target", target)
        assert env.ref("xp.nothing", raise_if_not_found=False) is None
        assert asked == [("xp.nothing", False)]


def test_ref_resolves_through_the_registry_port():
    with model_test_env(Thing, IrModelData) as env:
        thing = env["xp.thing"].create({"name": "t"})
        env["ir.model.data"].create(
            {"module": "xp", "name": "thing", "model": "xp.thing", "res_id": thing.id}
        )
        assert env.ref("xp.thing") == thing
        assert env.ref("xp.nothing", raise_if_not_found=False) is None
        with pytest.raises(ValueError, match="External ID not found"):
            env.ref("xp.nothing")
        # the unlink takes the external id with the record
        thing.unlink()
        assert env.ref("xp.thing", raise_if_not_found=False) is None
        # a stale entry names a record that is gone
        env["ir.model.data"].create(
            {"module": "xp", "name": "gone", "model": "xp.thing", "res_id": 999}
        )
        with pytest.raises(ValueError, match="may have been deleted"):
            env.ref("xp.gone")
