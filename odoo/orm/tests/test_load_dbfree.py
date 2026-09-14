from odoo import fields, models
from odoo.orm.model_test_env import ModelRegistry, model_test_env

from odoo.addons.base.models.ir_fields import IrFieldsConverter

_MOD = "test_load_dbfree"


class Tag(models.Model):
    _name = "ldf.tag"
    _module = _MOD
    _description = "tag"
    _log_access = False

    name = fields.Char()


class Doc(models.Model):
    _name = "ldf.doc"
    _module = _MOD
    _description = "a document imported through load()"
    _log_access = False

    name = fields.Char(required=True)
    qty = fields.Integer()
    price = fields.Float()
    flag = fields.Boolean()
    day = fields.Date()
    state = fields.Selection([("a", "A"), ("b", "B")])
    tag_ids = fields.Many2many("ldf.tag")
    main_tag_id = fields.Many2one("ldf.tag")


class IrModelData(models.Model):
    _name = "ir.model.data"
    _module = _MOD
    _description = "ir.model.data (load stub)"
    _log_access = False

    module = fields.Char()
    name = fields.Char()
    model = fields.Char()
    res_id = fields.Integer()
    noupdate = fields.Boolean()

    def _get_xmlids(self, xml_ids, model):
        # the seven-tuple the real model answers, the last item the res_id
        # when the target record still exists
        rows = []
        for xml_id in xml_ids:
            module, _dot, name = xml_id.partition(".")
            data = self.search([("module", "=", module), ("name", "=", name)])
            if data:
                alive = model.browse(data.res_id).exists()
                rows.append(
                    (
                        data.id,
                        data.module,
                        data.name,
                        data.model,
                        data.res_id,
                        data.noupdate,
                        data.res_id if alive else None,
                    )
                )
        return rows

    def _xmlid_to_res_model_res_id(self, xmlid, raise_if_not_found=False):
        module, _dot, name = xmlid.partition(".")
        data = self.search([("module", "=", module), ("name", "=", name)], limit=1)
        if data:
            return data.model, data.res_id
        if raise_if_not_found:
            raise ValueError(f"External ID not found in the system: {xmlid}")
        return (False, False)

    def _update_xmlids(self, entries, update=False):
        for entry in entries:
            module, _dot, name = entry["xml_id"].partition(".")
            record = entry["record"]
            existing = self.search([("module", "=", module), ("name", "=", name)])
            if existing:
                existing.res_id = record.id
            else:
                self.create(
                    {
                        "module": module,
                        "name": name,
                        "model": record._name,
                        "res_id": record.id,
                    }
                )


def _env(*extra):
    registry = ModelRegistry([Tag, Doc, IrFieldsConverter, *extra], isolated=True)
    return model_test_env(registry=registry)


HEADER = ["name", "qty", "price", "flag", "day", "state", "tag_ids", "main_tag_id"]


def test_load_converts_every_column_type_with_the_real_converter():
    with _env() as env:
        env["ldf.tag"].create([{"name": "red"}, {"name": "blue"}])
        result = env["ldf.doc"].load(
            HEADER,
            [
                ["a", "3", "1.5", "True", "2026-01-15", "A", "red,blue", "blue"],
                ["b", "7", "", "", "", "b", "", ""],
            ],
        )
        assert result["messages"] == []
        docs = env["ldf.doc"].browse(result["ids"])
        assert [
            (
                doc.name,
                doc.qty,
                doc.price,
                doc.flag,
                str(doc.day),
                doc.state,
                doc.tag_ids.mapped("name"),
                doc.main_tag_id.name,
            )
            for doc in docs
        ] == [
            ("a", 3, 1.5, True, "2026-01-15", "a", ["red", "blue"], "blue"),
            ("b", 7, 0.0, False, "False", "b", [], False),
        ]


def test_load_reports_a_bad_cell_by_row_and_field():
    with _env() as env:
        result = env["ldf.doc"].load(
            ["name", "qty", "state"], [["a", "x", "a"], ["b", "1", "nope"]]
        )
        assert result["ids"] is False
        assert [(m["type"], m["field"], m["rows"]) for m in result["messages"]] == [
            ("error", "qty", {"from": 0, "to": 0}),
            ("error", "state", {"from": 1, "to": 1}),
        ]


def test_load_with_external_ids_creates_then_updates():
    with _env(IrModelData) as env:
        Doc_ = env["ldf.doc"]
        first = Doc_.load(["id", "name", "qty"], [["ldf.one", "one", "1"]])
        assert first["messages"] == []
        again = Doc_.load(["id", "name", "qty"], [["ldf.one", "one again", "2"]])
        assert again["messages"] == []
        assert again["ids"] == first["ids"]
        doc = Doc_.browse(first["ids"])
        assert (doc.name, doc.qty) == ("one again", 2)
        assert env.ref("ldf.one") == doc


def test_an_import_prefix_naming_a_module_is_refused_through_the_metaschema(
    monkeypatch,
):
    with _env(IrModelData) as env:
        Doc_ = env["ldf.doc"].with_context(import_file=True)
        # no module table in memory: nothing to collide with
        assert Doc_.load(["id", "name"], [["sale.doc", "d"]])["messages"] == []
        monkeypatch.setattr(
            type(env.registry.metaschema), "module_names", lambda self, env: {"sale"}
        )
        result = Doc_.load(["id", "name"], [["sale.other", "o"]])
        assert [m["type"] for m in result["messages"]] == ["error"]
        assert "module prefix sale" in result["messages"][0]["message"]
