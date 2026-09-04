# Copyright 2013 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from unittest import mock

from odoo.addons.component.core import Component, WorkContext
from odoo.addons.component.tests.common import TransactionComponentRegistryCase
from odoo.addons.connector.components.mapper import (
    MapOptions,
    MappingDefinition,
    changed_by,
    convert,
    external_to_m2o,
    follow_m2o_relations,
    m2o_to_external,
    mapping,
    none,
    only_create,
)


class TestMapper(TransactionComponentRegistryCase):
    def setUp(self):
        super().setUp()
        self._setup_registry(self)
        self.comp_registry.load_components("connector")

    def test_mapping_decorator(self):
        class KifKrokerMapper(Component):
            _name = "kif.kroker.mapper"
            _inherit = "base.mapper"

            @changed_by("name", "city")
            @mapping
            @only_create
            def name(self):
                pass

            @changed_by("email")
            @mapping
            def email(self):
                pass

            @changed_by("street")
            @mapping
            def street(self):
                pass

            def no_decorator(self):
                pass

        # build our mapper component
        KifKrokerMapper._build_component(self.comp_registry)

        # what mappings we expect
        name_def = MappingDefinition(changed_by={"name", "city"}, only_create=True)
        email_def = MappingDefinition(changed_by={"email"}, only_create=False)
        street_def = MappingDefinition(changed_by={"street"}, only_create=False)

        # get our component by name in the components registry
        comp = self.comp_registry["kif.kroker.mapper"]
        # _map_methods contains the aggregated mapping methods for a Mapper
        self.assertEqual(
            comp._map_methods,
            {"name": name_def, "email": email_def, "street": street_def},
        )

    def test_mapping_decorator_cross_classes(self):
        """Mappings should not propagate to other classes"""

        class MomMapper(Component):
            _name = "mom.mapper"
            _inherit = "base.mapper"
            _apply_on = "res.users"

            @changed_by("name", "city")
            @mapping
            def name(self):
                pass

        class ZappMapper(Component):
            _name = "zapp.mapper"
            _inherit = "base.mapper"
            _apply_on = "res.users"

            @changed_by("email")
            @only_create
            @mapping
            def email(self):
                pass

        self._build_components(MomMapper, ZappMapper)

        mom_def = MappingDefinition(changed_by={"name", "city"}, only_create=False)
        zapp_def = MappingDefinition(changed_by={"email"}, only_create=True)

        comp = self.comp_registry["mom.mapper"]
        self.assertEqual(comp._map_methods, {"name": mom_def})
        comp = self.comp_registry["zapp.mapper"]
        self.assertEqual(comp._map_methods, {"email": zapp_def})

    def test_mapping_decorator_cumul(self):
        """Mappings should cumulate the ``super`` mappings
        and the local mappings."""

        class FryMapper(Component):
            _name = "fry.mapper"
            _inherit = "base.mapper"
            _apply_on = "res.users"

            @changed_by("name", "city")
            @mapping
            def name(self):
                pass

        # pylint: disable=R7980
        class FryMapperInherit(Component):
            _inherit = "fry.mapper"

            @changed_by("email")
            @mapping
            def email(self):
                pass

        self._build_components(FryMapper, FryMapperInherit)

        name_def = MappingDefinition(changed_by={"name", "city"}, only_create=False)
        email_def = MappingDefinition(changed_by={"email"}, only_create=False)

        comp = self.comp_registry["fry.mapper"]
        self.assertEqual(comp._map_methods, {"name": name_def, "email": email_def})

    def test_mapping_decorator_cumul_changed_by(self):
        """Mappings should cumulate the changed_by fields of the
        ``super`` mappings and the local mappings"""

        class FryMapper(Component):
            _name = "fry.mapper"
            _inherit = "base.mapper"
            _apply_on = "res.users"

            @changed_by("name", "city")
            @mapping
            def name(self):
                pass

        class FryMapperInherit(Component):
            _inherit = "fry.mapper"
            _apply_on = "res.users"

            @changed_by("email")
            @mapping
            def name(self):
                pass

        class ThirdMapper(Component):
            _name = "third.mapper"
            _inherit = "fry.mapper"
            _apply_on = "res.users"

            @changed_by("email", "street")
            @mapping
            def name(self):
                pass

        self._build_components(FryMapper, FryMapperInherit, ThirdMapper)

        name_def = MappingDefinition(
            changed_by={"name", "city", "email"}, only_create=False
        )

        comp = self.comp_registry["fry.mapper"]
        self.assertEqual(comp._map_methods, {"name": name_def})

        name_def = MappingDefinition(
            changed_by={"name", "city", "email", "street"}, only_create=False
        )
        comp = self.comp_registry["third.mapper"]
        self.assertEqual(comp._map_methods, {"name": name_def})

    def test_several_bases_cumul(self):
        class FryMapper(Component):
            _name = "fry.mapper"
            _inherit = "base.mapper"
            _apply_on = "res.users"

            @changed_by("name", "city")
            @mapping
            def name(self):
                pass

            @only_create
            @mapping
            def street(self):
                pass

            @only_create
            @mapping
            def zip(self):
                pass

        class FarnsworthMapper(Component):
            _name = "farnsworth.mapper"
            _inherit = "base.mapper"
            _apply_on = "res.users"

            @changed_by("email")
            @mapping
            def name(self):
                pass

            @changed_by("street")
            @mapping
            def city(self):
                pass

            @mapping
            def zip(self):
                pass

        class ThirdMapper(Component):
            _name = "third.mapper"
            _inherit = ["fry.mapper", "farnsworth.mapper"]
            _apply_on = "res.users"

            @changed_by("email", "street")
            @mapping
            def name(self):
                pass

            @mapping
            def email(self):
                pass

        self._build_components(FryMapper, FarnsworthMapper, ThirdMapper)

        name_def = MappingDefinition(
            changed_by={"name", "city", "email", "street"}, only_create=False
        )
        street_def = MappingDefinition(changed_by=set(), only_create=True)
        city_def = MappingDefinition(changed_by={"street"}, only_create=False)
        email_def = MappingDefinition(changed_by=set(), only_create=False)
        zip_def = MappingDefinition(changed_by=set(), only_create=True)

        comp = self.comp_registry["third.mapper"]
        self.assertEqual(comp._map_methods["name"], name_def)
        self.assertEqual(comp._map_methods["street"], street_def)
        self.assertEqual(comp._map_methods["city"], city_def)
        self.assertEqual(comp._map_methods["email"], email_def)
        self.assertEqual(comp._map_methods["zip"], zip_def)

    def test_mapping_record(self):
        """Map a record and check the result"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"
            _apply_on = "res.users"

            direct = [("name", "out_name")]

            @mapping
            def street(self, record):
                return {"out_street": record["street"].upper()}

        self._build_components(MyMapper)

        record = {"name": "Guewen", "street": "street"}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_name": "Guewen", "out_street": "STREET"}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(for_create=True), expected)

    def test_mapping_record_on_create(self):
        """Map a record and check the result for creation of record"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"
            _apply_on = "res.users"

            direct = [("name", "out_name")]

            @mapping
            def street(self, record):
                return {"out_street": record["street"].upper()}

            @only_create
            @mapping
            def city(self, record):
                return {"out_city": "city"}

        self._build_components(MyMapper)

        record = {"name": "Guewen", "street": "street"}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_name": "Guewen", "out_street": "STREET"}
        self.assertEqual(map_record.values(), expected)
        expected = {"out_name": "Guewen", "out_street": "STREET", "out_city": "city"}
        self.assertEqual(map_record.values(for_create=True), expected)

    def test_mapping_update(self):
        """Force values on a map record"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            direct = [("name", "out_name")]

            @mapping
            def street(self, record):
                return {"out_street": record["street"].upper()}

            @only_create
            @mapping
            def city(self, record):
                return {"out_city": "city"}

        self._build_components(MyMapper)

        record = {"name": "Guewen", "street": "street"}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        map_record.update({"test": 1}, out_city="forced")
        expected = {
            "out_name": "Guewen",
            "out_street": "STREET",
            "out_city": "forced",
            "test": 1,
        }
        self.assertEqual(map_record.values(), expected)
        expected = {
            "out_name": "Guewen",
            "out_street": "STREET",
            "out_city": "forced",
            "test": 1,
        }
        self.assertEqual(map_record.values(for_create=True), expected)

    # pylint: disable=W8110
    def test_finalize(self):
        """Inherit finalize to modify values"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            direct = [("name", "out_name")]

            def finalize(self, record, values):
                result = super().finalize(record, values)
                result["test"] = "abc"
                return result

        self._build_components(MyMapper)

        record = {"name": "Guewen", "street": "street"}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_name": "Guewen", "test": "abc"}
        self.assertEqual(map_record.values(), expected)
        expected = {"out_name": "Guewen", "test": "abc"}
        self.assertEqual(map_record.values(for_create=True), expected)

    def test_some_fields(self):
        """Map only a selection of fields"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            direct = [("name", "out_name"), ("street", "out_street")]

            @changed_by("country")
            @mapping
            def country(self, record):
                return {"country": "country"}

        self._build_components(MyMapper)

        record = {"name": "Guewen", "street": "street", "country": "country"}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_name": "Guewen", "country": "country"}
        self.assertEqual(map_record.values(fields=["name", "country"]), expected)
        expected = {"out_name": "Guewen", "country": "country"}
        self.assertEqual(
            map_record.values(for_create=True, fields=["name", "country"]), expected
        )

    def test_mapping_modifier(self):
        """Map a direct record with a modifier function"""

        def do_nothing(field):
            def transform(self, record, to_attr):
                return record[field]

            return transform

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            direct = [(do_nothing("name"), "out_name")]

        self._build_components(MyMapper)

        record = {"name": "Guewen"}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_name": "Guewen"}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(for_create=True), expected)

    def test_mapping_direct_property(self):
        """Map a direct record with 'direct' being a property"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            @property
            def direct(self):
                return [("name", "out_name")]

        self._build_components(MyMapper)

        record = {"name": "Foo"}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_name": "Foo"}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(for_create=True), expected)

    def test_mapping_convert(self):
        """Map a direct record with the convert modifier function"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            direct = [(convert("name", int), "out_name")]

        self._build_components(MyMapper)

        record = {"name": "300"}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_name": 300}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(for_create=True), expected)

    def test_mapping_modifier_none(self):
        """Pipeline of modifiers"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            direct = [(none("in_f"), "out_f"), (none("in_t"), "out_t")]

        self._build_components(MyMapper)

        record = {"in_f": False, "in_t": True}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_f": None, "out_t": True}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(for_create=True), expected)

    def test_mapping_modifier_pipeline(self):
        """Pipeline of modifiers"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            direct = [
                (none(convert("in_f", bool)), "out_f"),
                (none(convert("in_t", bool)), "out_t"),
            ]

        self._build_components(MyMapper)

        record = {"in_f": 0, "in_t": 1}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_f": None, "out_t": True}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(for_create=True), expected)

    def test_modifier_import_filter_field(self):
        """A direct mapping with a modifier must still be considered
        from the list of fields
        """

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            direct = [
                ("field", "field2"),
                ("no_field", "no_field2"),
                (convert("name", int), "out_name"),
            ]

        self._build_components(MyMapper)

        record = {"name": "300", "field": "value", "no_field": "no_value"}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_name": 300, "field2": "value"}
        self.assertEqual(map_record.values(fields=["field", "name"]), expected)
        self.assertEqual(
            map_record.values(for_create=True, fields=["field", "name"]), expected
        )

    def test_modifier_export_filter_field(self):
        """A direct mapping with a modifier on an export mapping"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.export.mapper"

            direct = [
                ("field", "field2"),
                ("no_field", "no_field2"),
                (convert("name", int), "out_name"),
            ]

        self._build_components(MyMapper)

        record = {"name": "300", "field": "value", "no_field": "no_value"}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"out_name": 300, "field2": "value"}
        self.assertEqual(map_record.values(fields=["field", "name"]), expected)
        self.assertEqual(
            map_record.values(for_create=True, fields=["field", "name"]), expected
        )

    def test_mapping_custom_option(self):
        """Usage of custom options in mappings"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            @mapping
            def any(self, record):
                if self.options.custom:
                    res = True
                else:
                    res = False
                return {"res": res}

        self._build_components(MyMapper)

        record = {}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"res": True}
        self.assertEqual(map_record.values(custom=True), expected)

    def test_mapping_custom_option_not_defined(self):
        """Usage of custom options not defined raise AttributeError"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            @mapping
            def any(self, record):
                if self.options.custom is None:
                    res = True
                else:
                    res = False
                return {"res": res}

        self._build_components(MyMapper)

        record = {}
        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)
        map_record = mapper.map_record(record)
        expected = {"res": True}
        self.assertEqual(map_record.values(), expected)

    def test_map_options(self):
        """Test MapOptions"""
        options = MapOptions({"xyz": "abc"}, k=1)
        options.l = 2  # noqa: E741
        self.assertEqual(options["xyz"], "abc")
        self.assertEqual(options["k"], 1)
        self.assertEqual(options["l"], 2)
        self.assertEqual(options.xyz, "abc")
        self.assertEqual(options.k, 1)
        self.assertEqual(options.l, 2)
        self.assertEqual(options["undefined"], None)
        self.assertEqual(options.undefined, None)

    def test_changed_by_fields(self):
        """Test attribute ``_changed_by_fields`` on Mapper."""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.export.mapper"

            direct = [
                ("street", "out_street"),
                (none("in_t"), "out_t"),
                (none(convert("in_f", bool)), "out_f"),
            ]

            @changed_by("name", "city")
            @mapping
            def name(self):
                pass

            @changed_by("email")
            @mapping
            def email(self):
                pass

            def no_decorator(self):
                pass

        self._build_components(MyMapper)

        work = mock.MagicMock(name="WorkContext()")
        mapper = self.comp_registry["my.mapper"](work)

        self.assertEqual(
            mapper.changed_by_fields(),
            {"street", "in_t", "in_f", "name", "city", "email"},
        )


class TestMapperRecordsets(TransactionComponentRegistryCase):
    """Test mapper with "real" records instead of mocks"""

    def setUp(self):
        super().setUp()
        self._setup_registry(self)
        self.comp_registry.load_components("connector")

        backend_record = mock.Mock()
        backend_record.env = self.env
        self.work = WorkContext(
            model_name="res.partner",
            collection=backend_record,
            components_registry=self.comp_registry,
        )

    def test_mapping_modifier_follow_m2o_relations(self):
        """Map with the follow_m2o_relations modifier"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"

            direct = [(follow_m2o_relations("parent_id.name"), "parent_name")]

        self._build_components(MyMapper)

        partner = self.env.ref("base.res_partner_address_4")
        mapper = self.comp_registry["my.mapper"](self.work)
        map_record = mapper.map_record(partner)
        expected = {"parent_name": "Deco Addict"}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(for_create=True), expected)


class TestMapperBinding(TransactionComponentRegistryCase):
    """Test Mapper with Bindings"""

    def setUp(self):
        super().setUp()
        self._setup_registry(self)
        self.comp_registry.load_components("connector")

        backend_record = mock.Mock()
        backend_record.env = self.env
        backend_record._name = "my.collection"
        self.work = WorkContext(
            model_name="res.partner",
            collection=backend_record,
            components_registry=self.comp_registry,
        )

        self.country_binder = mock.MagicMock(name="country_binder")
        self.country_binder.return_value = self.country_binder
        self.country_binder._name = "test.binder"
        self.country_binder._inherit = "base.binder"
        self.country_binder.apply_on_models = ["res.country"]
        self.country_binder._usage = "binder"
        self.country_binder._collection = "my.collection"
        self.country_binder._abstract = False
        self.comp_registry["test.binder"] = self.country_binder

    def test_mapping_m2o_to_external(self):
        """Map a direct record with the m2o_to_external modifier function"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"
            _apply_on = "res.partner"

            direct = [(m2o_to_external("country_id"), "country")]

        self._build_components(MyMapper)

        partner = self.env.ref("base.main_partner")
        partner.write({"country_id": self.env.ref("base.ch").id})
        self.country_binder.to_external.return_value = 10

        mapper = self.comp_registry["my.mapper"](self.work)
        map_record = mapper.map_record(partner)
        self.assertEqual(map_record.values(), {"country": 10})
        self.country_binder.to_external.assert_called_once_with(
            partner.country_id.id, wrap=False
        )

    def test_mapping_backend_to_m2o(self):
        """Map a direct record with the backend_to_m2o modifier function"""

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"
            _apply_on = "res.partner"

            direct = [(external_to_m2o("country"), "country_id")]

        self._build_components(MyMapper)

        record = {"country": 10}
        ch = self.env.ref("base.ch")
        self.country_binder.to_internal.return_value = ch
        mapper = self.comp_registry["my.mapper"](self.work)
        map_record = mapper.map_record(record)
        self.assertEqual(map_record.values(), {"country_id": ch.id})
        self.country_binder.to_internal.assert_called_once_with(10, unwrap=False)

    def test_mapping_record_children_no_map_child(self):
        """Map a record with children, using default MapChild"""
        # we need these components which make the 'link' between
        # the main mapper and the line mapper

        class LineMapper(Component):
            _name = "line.mapper"
            _inherit = "base.import.mapper"
            _apply_on = "res.currency.rate"

            direct = [("name", "name")]

            @mapping
            def price(self, record):
                return {"rate": record["rate"] * 2}

            @only_create
            @mapping
            def discount(self, record):
                return {"test": 0.5}

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"
            _apply_on = "res.currency"

            direct = [("name", "name")]

            children = [("lines", "line_ids", "res.currency.rate")]

        self._build_components(LineMapper, MyMapper)

        record = {
            "name": "SO1",
            "lines": [
                {"name": "2013-11-07", "rate": 10},
                {"name": "2013-11-08", "rate": 20},
            ],
        }
        mapper = self.comp_registry["my.mapper"](self.work)
        map_record = mapper.map_record(record)
        expected = {
            "name": "SO1",
            "line_ids": [
                (0, 0, {"name": "2013-11-07", "rate": 20}),
                (0, 0, {"name": "2013-11-08", "rate": 40}),
            ],
        }
        self.assertEqual(map_record.values(), expected)
        expected = {
            "name": "SO1",
            "line_ids": [
                (0, 0, {"name": "2013-11-07", "rate": 20, "test": 0.5}),
                (0, 0, {"name": "2013-11-08", "rate": 40, "test": 0.5}),
            ],
        }
        self.assertEqual(map_record.values(for_create=True), expected)

    def test_mapping_record_children(self):
        """Map a record with children, using defined MapChild"""
        # we need these components which make the 'link' between
        # the main mapper and the line mapper

        class LineMapper(Component):
            _name = "line.mapper"
            _inherit = "base.import.mapper"
            _apply_on = "res.currency.rate"

            direct = [("name", "name")]

            @mapping
            def price(self, record):
                return {"rate": record["rate"] * 2}

            @only_create
            @mapping
            def discount(self, record):
                return {"test": 0.5}

        class LineImportMapChild(Component):
            _name = "line.map.child.import"
            _inherit = "base.map.child.import"
            _apply_on = "res.currency.rate"

            def format_items(self, items_values):
                return [("ABC", values) for values in items_values]

        class MyMapper(Component):
            _name = "my.mapper"
            _inherit = "base.import.mapper"
            _apply_on = "res.currency"

            direct = [("name", "name")]

            children = [("lines", "line_ids", "res.currency.rate")]

        self._build_components(LineMapper, LineImportMapChild, MyMapper)

        record = {
            "name": "SO1",
            "lines": [
                {"name": "2013-11-07", "rate": 10},
                {"name": "2013-11-08", "rate": 20},
            ],
        }
        mapper = self.comp_registry["my.mapper"](self.work)
        map_record = mapper.map_record(record)
        expected = {
            "name": "SO1",
            "line_ids": [
                ("ABC", {"name": "2013-11-07", "rate": 20}),
                ("ABC", {"name": "2013-11-08", "rate": 40}),
            ],
        }
        self.assertEqual(map_record.values(), expected)
        expected = {
            "name": "SO1",
            "line_ids": [
                ("ABC", {"name": "2013-11-07", "rate": 20, "test": 0.5}),
                ("ABC", {"name": "2013-11-08", "rate": 40, "test": 0.5}),
            ],
        }
        self.assertEqual(map_record.values(for_create=True), expected)

    def test_mapping_record_children_void(self):
        """Map a record with children, using defined MapChild"""

        class LineMapper(Component):
            _name = "line.mapper"
            _inherit = "base.import.mapper"
            _apply_on = "res.currency.rate"

            @mapping
            def price(self, record):
                rate = record.get("rate")
                if rate and rate < 40:
                    return {"rate": record["rate"] * 2}

        class SaleLineImportMapChild(Component):
            _name = "sale.line.mapper"
            _inherit = "base.map.child.import"
            _apply_on = "res.currency.rate"

            def format_items(self, items_values):
                return [("ABC", values) for values in items_values]

        class ObjectMapper(Component):
            _name = "currency.mapper"
            _inherit = "base.import.mapper"
            _apply_on = "res.currency"

            direct = [("name", "name")]

            children = [("lines", "line_ids", "res.currency.rate")]

        self._build_components(ObjectMapper, SaleLineImportMapChild, LineMapper)

        # Test with an excluded child record
        record = {
            "name": "SO1",
            "lines": [{"rate": 10}, {"rate": 20}, {"rate": 30}, {"rate": 40}],
        }
        mapper = self.comp_registry["currency.mapper"](self.work)
        map_record = mapper.map_record(record)

        expected = {
            "name": "SO1",
            "line_ids": [
                ("ABC", {"rate": 20}),
                ("ABC", {"rate": 40}),
                ("ABC", {"rate": 60}),
            ],
        }
        self.assertEqual(map_record.values(), expected)
