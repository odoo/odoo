import pytest

from odoo.modules import loading

from .conftest import requires_pg


@pytest.fixture
def imd(scratch_cursor):
    scratch_cursor.execute(
        """
        CREATE TEMP TABLE ir_model_data (
            module text NOT NULL,
            name text NOT NULL,
            PRIMARY KEY (module, name)
        ) ON COMMIT DROP
        """
    )
    return scratch_cursor


def _present(cr, *xmlids):
    for xmlid in xmlids:
        module, _, name = xmlid.partition(".")
        cr.execute(
            "INSERT INTO ir_model_data (module, name) VALUES (%s, %s)", (module, name)
        )


def _entry(*xmlids):
    return {"sha": "irrelevant", "xmlids": list(xmlids), "dyn": False}


@requires_pg
class TestFilesMissingRecordsAgainstPostgres:
    def test_the_xmlid_list_binds_as_an_array(self, imd):
        _present(imd, "mymod.a")
        assert (
            loading._files_missing_records(imd, {"data/x.xml": _entry("mymod.a")})
            == set()
        ), (
            "a plain Python list of str reaches PostgreSQL as `unknown`, and "
            "unnest() is overloaded, so the query is rejected with "
            "AmbiguousFunction unless the parameter carries its own cast. The "
            "mocked cursor in tests/loading cannot see this: it never sends SQL"
        )

    def test_a_missing_record_names_its_file(self, imd):
        _present(imd, "mymod.a")
        stale = loading._files_missing_records(
            imd,
            {
                "data/x.xml": _entry("mymod.a"),
                "views/y.xml": _entry("mymod.b"),
            },
        )
        assert stale == {"views/y.xml"}

    def test_a_record_declared_by_two_files_names_both(self, imd):
        stale = loading._files_missing_records(
            imd, {"data/x.xml": _entry("mymod.a"), "views/y.xml": _entry("mymod.a")}
        )
        assert stale == {"data/x.xml", "views/y.xml"}

    def test_an_xmlid_whose_name_carries_a_dot_is_split_on_the_first_one(self, imd):
        _present(imd, "mymod.res.partner.form")
        assert (
            loading._files_missing_records(
                imd, {"data/x.xml": _entry("mymod.res.partner.form")}
            )
            == set()
        ), (
            "the module is everything before the FIRST dot and the name is the "
            "whole remainder; splitting on the last one, or taking the second "
            "component as the name, reports a present record as missing and "
            "re-applies the file on every upgrade"
        )

    def test_a_module_named_like_another_is_not_confused(self, imd):
        _present(imd, "mymod.a")
        stale = loading._files_missing_records(
            imd, {"data/x.xml": _entry("mymod_extra.a")}
        )
        assert stale == {"data/x.xml"}, (
            "mymod_extra.a is a different record from mymod.a; matching on the "
            "module prefix rather than the whole component would hide it"
        )


@pytest.fixture
def imd_ids(scratch_cursor):
    scratch_cursor.execute(
        """
        CREATE TEMP TABLE ir_model_data (
            module text NOT NULL,
            name text NOT NULL,
            res_id integer,
            PRIMARY KEY (module, name)
        ) ON COMMIT DROP
        """
    )
    return scratch_cursor


def _resolving(cr, xmlid, res_id):
    module, _, name = xmlid.partition(".")
    cr.execute(
        "INSERT INTO ir_model_data (module, name, res_id) VALUES (%s, %s, %s)",
        (module, name, res_id),
    )


def _referencing(**refs):
    return {"sha": "irrelevant", "xmlids": [], "refs": refs, "dyn": False}


@requires_pg
class TestFilesWithMovedRefsAgainstPostgres:
    def test_the_two_arrays_bind_and_a_held_reference_names_nothing(self, imd_ids):
        _resolving(imd_ids, "website.configurator_s_cover", 1079)
        assert (
            loading._files_with_moved_refs(
                imd_ids,
                {"views/x.xml": _referencing(**{"website.configurator_s_cover": 1079})},
            )
            == set()
        )

    def test_a_recreated_record_names_the_file_that_referenced_it(self, imd_ids):
        _resolving(imd_ids, "website.configurator_s_cover", 4042)
        _resolving(imd_ids, "website.layout", 12)
        stale = loading._files_with_moved_refs(
            imd_ids,
            {
                "views/x.xml": _referencing(**{"website.configurator_s_cover": 1079}),
                "views/y.xml": _referencing(**{"website.layout": 12}),
            },
        )
        assert stale == {"views/x.xml"}

    def test_a_reference_gone_altogether_names_the_file(self, imd_ids):
        stale = loading._files_with_moved_refs(
            imd_ids, {"views/x.xml": _referencing(**{"website.gone": 5})}
        )
        assert stale == {"views/x.xml"}
