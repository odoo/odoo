from operator import itemgetter

from lxml import etree

from odoo import Command
from odoo.tests import Form, TransactionCase


class TestFormFields(TransactionCase):
    def test_form_create(self):
        form = Form(self.env['test_testing_utilities.form_create'])

        self.assertEqual(form.id, False)

        form.field = 42

        with self.assertRaises(AssertionError):
            form.record

        record = form.save()

        self.assertEqual(record.field, 42)
        self.assertEqual(form.record, record)

    def test_form_field_with_default(self):
        form = Form(self.env['test_testing_utilities.form_default'])

        self.assertEqual(form.field_default, 42)

        record = form.save()

        self.assertEqual(record.field_default, 42)

    def test_form_field_with_onchange(self):
        form = Form(self.env['test_testing_utilities.form_onchange'])

        self.assertEqual(form.field_onchange, 0)

        form.field_trigger_onchange = 84

        self.assertEqual(form.field_onchange, 42)

        record = form.save()

        self.assertEqual(record.field_onchange, 42)

    def test_form_field_with_compute(self):
        form = Form(self.env['test_testing_utilities.form_compute'])

        self.assertEqual(form.field_compute, 0)

        form.field_trigger_compute = 84

        self.assertEqual(form.field_compute, 42)

        record = form.save()

        self.assertEqual(record.field_compute, 42)

    def test_form_field_with_required(self):
        form = Form(self.env['test_testing_utilities.form_required'])

        self.assertEqual(form.field_required, False)

        with self.assertRaises(AssertionError):
            form.save()

        form.field_required = '42'

        self.assertEqual(form.field_required, '42')

        record = form.save()

        self.assertEqual(record.field_required, '42')

    def test_form_field_with_required_from_xml(self):
        form = Form(self.env['test_testing_utilities.form_required_xml'], view='test_testing_utilities.form_required')

        self.assertEqual(form.field_required, False)

        with self.assertRaises(AssertionError):
            form.save()

        form.field_required = '42'

        self.assertEqual(form.field_required, '42')

        record = form.save()

        self.assertEqual(record.field_required, '42')

    def test_form_boolean_with_required(self):
        form = Form(self.env['test_testing_utilities.form_required_boolean'])

        form.field_required_boolean = False

        record = form.save()

        self.assertEqual(record.field_required_boolean, False)

    def test_form_empty_boolean_with_required(self):
        form = Form(self.env['test_testing_utilities.form_required_boolean'])

        record = form.save()

        self.assertEqual(record.field_required_boolean, False)

    def test_form_field_with_readonly(self):
        form = Form(self.env['test_testing_utilities.form_readonly'])

        with self.assertRaises(AssertionError):
            form.field_readonly = '42'

    def test_form_field_with_readonly_from_xml_and_force_save(self):
        form = Form(self.env['test_testing_utilities.form_readonly_xml'], view='test_testing_utilities.readonly')

        form.field_trigger_without_force_save = 42
        form.field_trigger_with_force_save = 42

        self.assertEqual(form.field_without_force_save, 42)
        self.assertEqual(form.field_with_force_save, 42)

        record = form.save()

        self.assertEqual(record.field_without_force_save, 0)
        self.assertEqual(record.field_with_force_save, 42)

    def test_form_field_with_conditional_readonly_from_xml(self):
        form = Form(self.env['test_testing_utilities.form_readonly_xml'], view='test_testing_utilities.form_readonly')

        # field_with_condition is not readonly yet.
        form.field_with_condition = 42

        # Make field_with_condition readonly.
        form.field_trigger_condition = 42

        with self.assertRaises(AssertionError):
            form.field_with_condition = 43

    def test_form_field_with_compute_and_without_inverse(self):
        form = Form(self.env['test_testing_utilities.form_readonly'])

        with self.assertRaises(AssertionError):
            form.field_compute_readonly = 42


class TestM2O(TransactionCase):
    def test_default(self):
        form_before_record = Form(self.env['test_testing_utilities.m2o_default'])

        self.assertFalse(form_before_record.field_default)

        with self.assertRaises(AssertionError):
            form_before_record.save()

        record = self.env['test_testing_utilities.m2o'].create({'name': "trigger_default"})
        form_after_record = Form(self.env['test_testing_utilities.m2o_default'])

        self.assertEqual(form_after_record.field_default, record)

        form_after_record.save()

    def test_onchange(self):
        form_before_record = Form(self.env['test_testing_utilities.m2o_onchange'])

        self.assertFalse(form_before_record.field_onchange)

        record = self.env['test_testing_utilities.m2o'].create({'name': "trigger_onchange"})

        form_after_record = Form(self.env['test_testing_utilities.m2o_onchange'])

        form_after_record.field_trigger_onchange = "trigger_onchange"
        self.assertEqual(form_after_record.field_onchange, record)

        form_after_record.save()

    def test_many_2_one(self):
        record = self.env['test_testing_utilities.m2o'].create({'name': "A"})

        form = Form(self.env['test_testing_utilities.m2o_xxx'])

        form.field_m2o = record
        self.assertEqual(form.field_m2o, record)

        record_saved = form.save()
        self.assertEqual(record_saved.field_m2o, record)

    def test_m2o_set_id(self):
        record = self.env['test_testing_utilities.m2o'].create({'name': "A"})

        form = Form(self.env['test_testing_utilities.m2o_xxx'])

        form.field_m2o = record
        self.assertEqual(form.field_m2o, record)

        with self.assertRaises(AssertionError):
            form.field_m2o = record.id

        form.field_m2o = record
        self.assertEqual(form.field_m2o, record)

    def test_m2o_wrong_model(self):
        record = self.env['test_testing_utilities.m2o'].create({'name': "A"})
        wrong_record = self.env['test_testing_utilities.m2o_xxx'].create({})

        form = Form(self.env['test_testing_utilities.m2o_xxx'])

        form.field_m2o = record
        self.assertEqual(form.field_m2o, record)

        with self.assertRaises(AssertionError):
            form.field_m2o = wrong_record

        form.field_m2o = record
        self.assertEqual(form.field_m2o, record)

    def test_compute(self):
        pass


class TestM2M(TransactionCase):
    def test_m2m(self):
        model = self.env['test.dummy']
        record_1 = model.create({'name': "Item"})
        record_2 = model.create({'name': "Item"})

        with Form(self.env['test.m2m']) as form:
            form.field_m2m.add(record_1)
            form.field_m2m.add(record_2)

        self.assertEqual(form.record.field_m2m, record_1 | record_2)

    def test_remove_by_index(self):
        model = self.env['test.dummy']
        record_1 = model.create({'name': "Item"})
        record_2 = model.create({'name': "Item2"})

        with Form(self.env['test.m2m']) as form:
            form.field_m2m.add(record_1)
            form.field_m2m.add(record_2)
            form.field_m2m.remove(index=0)

        self.assertEqual(
            form.record.field_m2m,
            record_2,
        )

    def test_remove_by_id(self):
        model = self.env['test.dummy']
        record_1 = model.create({'name': "Item"})
        record_2 = model.create({'name': "Item2"})

        with Form(self.env['test.m2m']) as form:
            form.field_m2m.add(record_1)
            form.field_m2m.add(record_2)
            form.field_m2m.remove(id=record_1.id)

        self.assertEqual(
            form.record.field_m2m,
            record_2,
        )

    def test_set(self):
        model = self.env['test.dummy']
        record_1 = model.create({'name': "Item"})
        record_2 = model.create({'name': "Item2"})
        record_3 = model.create({'name': "Item3"})

        with Form(self.env['test.m2m']) as form:
            form.field_m2m.set(record_1 + record_2)

        self.assertEqual(form.record.field_m2m, record_1 + record_2)

        with form:
            form.field_m2m = record_3

        self.assertEqual(form.record.field_m2m, record_3)

    def test_compute(self):
        model = self.env['test.dummy']
        form = Form(self.env['test.m2m_compute'])

        self.assertEqual(form.field_compute, 0)

        form.field_trigger_compute.add(model.create({'name': 'a'}))
        self.assertEqual(form.field_compute, 1)

        form.field_trigger_compute.add(model.create({'name': 'a'}))
        form.field_trigger_compute.add(model.create({'name': 'a'}))
        form.field_trigger_compute.add(model.create({'name': 'a'}))
        self.assertEqual(form.field_compute, 4)

        form.field_trigger_compute.remove(index=0)
        form.field_trigger_compute.remove(index=0)
        form.field_trigger_compute.remove(index=0)
        self.assertEqual(form.field_compute, 1)

    def test_default(self):
        model = self.env['test.dummy']
        record_1 = model.create({'name': 'a'})
        record_2 = model.create({'name': 'b'})

        form = Form(self.env['test.m2m_default'])

        self.assertEqual(form.field_default[:], record_1 | record_2)

    def test_onchange(self):
        model = self.env['test.dummy']
        a = model.create({'name': 'a'})
        b = model.create({'name': 'b'})

        form = Form(self.env['test.m2m_onchange'])

        form.field_trigger_onchange = a
        self.assertEqual(form.field_onchange[:], a)

        form.field_trigger_onchange = b
        self.assertEqual(form.field_onchange[:], a | b)

    def test_m2m_changed(self):
        r1 = self.env['test_testing_utilities.m2o'].create({'name': "A"})
        r2 = self.env['test_testing_utilities.m2o'].create({'name': "B"})

        Sub = self.env['test_testing_utilities.sub2']
        a = Sub.create({'name': 'a'})
        b = Sub.create({'name': 'b'})
        c = Sub.create({'name': 'c', 'm2o_ids': [Command.set([r1.id, r2.id])]})
        d = Sub.create({'name': 'd'})

        f = Form(self.env['test_testing_utilities.f'])
        # check default_get
        self.assertEqual(f.m2m[:], a | b)

        f.m2o = c
        self.assertEqual(f.m2m[:], a | b | c)

        f.m2o = d
        self.assertEqual(f.m2m[:], a | b | c | d)

    def test_readonly(self):
        pass

    def test_m2m_readonly(self):
        Sub = self.env['test_testing_utilities.sub3']
        a = Sub.create({'name': 'a'})
        b = Sub.create({'name': 'b'})
        r = self.env['test_testing_utilities.g'].create({
            'm2m': [Command.set(a.ids)],
        })

        f = Form(r)

        with self.assertRaises(AssertionError):
            f.m2m.add(b)
        with self.assertRaises(AssertionError):
            f.m2m.remove(id=a.id)

        f.save()
        self.assertEqual(r.m2m, a)

    def test_attr(self):
        f = Form(self.env['test_testing_utilities.e'], view='test_testing_utilities.attrs_using_m2m')
        with self.assertRaises(AssertionError):
            f.count = 5
        f.m2m.add(self.env['test_testing_utilities.sub2'].create({'name': 'ok'}))
        f.count = 5
        r = f.save()
        self.assertEqual(
            r.m2m.mapped('name'),
            ['ok', '1', '2', '3', '4'],
        )


get = itemgetter('name', 'value', 'v')


class TestO2M(TransactionCase):
    def test_basic_alterations(self):
        """ Tests that the o2m proxy allows adding, removing and editing o2m
        records
        """
        with Form(self.env['test_testing_utilities.parent'], view='test_testing_utilities.o2m_parent') as f:
            f.subs.new().save()
            f.subs.new().save()
            f.subs.new().save()
            f.subs.remove(index=0)

        r = f.record

        self.assertEqual(
            [get(s) for s in r.subs],
            [("2", 2, 2), ("2", 2, 2)],
        )
        self.assertEqual(r.v, 5)

        with Form(r, view='test_testing_utilities.o2m_parent') as f:
            with f.subs.new() as sub:
                sub.value = 5
            f.subs.new().save()

            with f.subs.edit(index=2) as sub:
                self.assertEqual(sub.v, 5)

            f.subs.remove(index=0)

        self.assertEqual(
            [get(s) for s in r.subs],
            [("2", 2, 2), ("5", 5, 5), ("2", 2, 2)],
        )
        self.assertEqual(r.v, 10)

        with Form(r, view='test_testing_utilities.o2m_parent') as f, \
            f.subs.edit(index=0) as sub,\
            self.assertRaises(AssertionError):
                sub.name = "whop whop"

    def test_o2m_editable_list(self):
        """ Tests the o2m proxy when the list view is editable rather than
        delegating to a separate form view
        """
        f = Form(self.env['test_testing_utilities.parent'], view='test_testing_utilities.o2m_parent_ed')
        custom_tree = self.env.ref('test_testing_utilities.editable_external')

        self.assertEqual(
            [el.get('name') for el in f._view['tree'].xpath('//field[@name="subs"]/list//field')],
            [el.get('name') for el in etree.fromstring(custom_tree['arch']).xpath('//field')],
            'check that the list view is the one referenced by list_view_ref',
        )
        subs_field = f._view['fields']['subs']
        self.assertIs(subs_field['edition_view']['tree'], f._view['tree'].xpath('//field[@name="subs"]/list')[0], "check that the edition view is the list view")
        self.assertEqual(
            [el.get('name') for el in subs_field['edition_view']['tree'].xpath('.//field')],
            [el.get('name') for el in etree.fromstring(custom_tree['arch']).xpath('//field')],
        )

        with f.subs.new() as s:
            s.value = 1
        with f.subs.new() as s:
            s.value = 3
        with f.subs.new() as s:
            s.value = 7

        r = f.save()

        self.assertEqual(r.v, 12)
        self.assertEqual(
            [get(s) for s in r.subs],
            [('1', 1, 1), ('3', 3, 3), ('7', 7, 7)],
        )

    def test_o2m_inline(self):
        """ Tests the o2m proxy when the list and form views are provided
        inline rather than fetched separately
        """
        with Form(self.env['test_testing_utilities.parent'], view='test_testing_utilities.o2m_parent_inline') as f:
            with f.subs.new() as s:
                s.value = 42

        r = f.record

        self.assertEqual(
            [get(s) for s in r.subs],
            [("0", 42, 0)],
            "should not have set v (and thus not name)",
        )

    def test_o2m_parent_context(self):
        """ Test the o2m form with a context on the field that uses 'parent'. """
        view = 'test_testing_utilities.o2m_parent_context'
        with Form(self.env['test_testing_utilities.parent'], view=view) as f:
            with f.subs.new() as s:
                s.value = 42

    def test_o2m_default(self):
        """ Tests that default_get can return defaults for the o2m
        """
        with Form(self.env['test_testing_utilities.default']) as f:
            with f.subs.edit(index=0) as s:
                self.assertEqual(s.v, 5)
                self.assertEqual(s.value, 2)

        r = f.record

        self.assertEqual(
            [get(s) for s in r.subs],
            [("5", 2, 5)],
        )

    def test_o2m_inner_default(self):
        """ Tests that creating an o2m record will get defaults for it
        """
        with Form(self.env['test_testing_utilities.default']) as f:
            with f.subs.new() as s:
                self.assertEqual(s.value, 2)
                self.assertEqual(s.v, 2, "should have onchanged value to v")

    def test_o2m_default_discarded(self):
        """ Tests what happens when the default value is discarded. """
        model = self.env['test_testing_utilities.default']
        with Form(model.with_context(default_value=42)) as f:
            self.assertFalse(len(f.subs))

    def test_o2m_onchange_parent(self):
        """ Tests that changing o2m content triggers onchange in the parent
        """
        f = Form(self.env['test_testing_utilities.parent'])

        self.assertEqual(f.value, 1, "value should have its default")
        self.assertEqual(f.v, 1, "v should be equal to value")

        f.subs.new().save()

        self.assertEqual(f.v, 3, "should be sum of value & children v")

    def test_o2m_onchange_inner(self):
        """ Tests that editing a field of an o2m record triggers onchange
        in the o2m record and its parent
        """
        f = Form(self.env['test_testing_utilities.parent'])

        # only apply the onchange on edition end (?)
        with f.subs.new() as sub:
            sub.value = 6
            self.assertEqual(sub.v, 6)
            self.assertEqual(f.v, 1)
        self.assertEqual(f.v, 7)

    def test_o2m_parent_content(self):
        """ Tests that when editing a field of an o2m the data sent contains
        the parent data
        """
        f = Form(self.env['test_testing_utilities.parent'])

        # only apply the onchange on edition end (?)
        with f.subs.new() as sub:
            sub.has_parent = True
            self.assertEqual(sub.has_parent, True)
            self.assertEqual(sub.value, 1)
            self.assertEqual(sub.v, 1)

    def test_readonly_o2m(self):
        """ Tests that o2m fields flagged as readonly (readonly="1" in the
        view) can't be written to
        """
        r = self.env['test_testing_utilities.parent'].create({
            'subs': [Command.create({})],
        })
        f = Form(r, view='test_testing_utilities.o2m_parent_readonly')

        with self.assertRaises(AssertionError):
            f.subs.new()
        with self.assertRaises(AssertionError):
            f.subs.edit(index=0)
        with self.assertRaises(AssertionError):
            f.subs.remove(index=0)

    def test_o2m_readonly_subfield(self):
        """ Tests that readonly is applied to the field of the o2m = not sent
        as part of the create / write values
        """
        with Form(self.env['o2m_readonly_subfield_parent']) as f:
            with f.line_ids.new() as new_line:
                new_line.name = "ok"
                self.assertEqual(new_line.f, 2)
        r = f.record
        self.assertEqual(
            (r.line_ids.name, r.line_ids.f),
            ('ok', 2),
        )

    def test_o2m_dyn_onchange(self):
        f = Form(self.env['test_testing_utilities.onchange_parent'], view='test_testing_utilities.m2o_onchange_view')

        with f.line_ids.new() as new_line:
            new_line.dummy = 42
            self.assertTrue(new_line.flag)

        with f.line_ids.edit(index=0) as new_line:
            self.assertTrue(new_line.flag)

    def test_o2m_remove(self):
        def commands():
            return [c[0] for c in f._values['line_ids'].to_commands()]

        with Form(self.env['test_testing_utilities.onchange_count']) as f:
            self.assertEqual(f.count, 0)
            self.assertEqual(len(f.line_ids), 0)

            f.count = 5
            self.assertEqual(f.count, 5)
            self.assertEqual(len(f.line_ids), 5)

            f.count = 2
            self.assertEqual(f.count, 2)
            self.assertEqual(len(f.line_ids), 2)

            f.count = 4

        r = f.record

        previous = r.line_ids
        self.assertEqual(len(previous), 4)

        with Form(r) as f:
            f.count = 2
            self.assertEqual(commands(), [0, 0, 2, 2, 2, 2], "Should contain 2 creations and 4 deletions")
        self.assertEqual(len(r.line_ids), 2)

        with Form(r) as f:
            f.line_ids.remove(0)
            self.assertEqual(commands(), [2])
            f.count = 1
            self.assertEqual(commands(), [0, 2, 2], "should contain 1 creation and 2 deletions")
        self.assertEqual(len(r.line_ids), 1)

    def test_o2m_self_recursive(self):
        Form(self.env['test_testing_utilities.recursive'], view='test_testing_utilities.o2m_recursive_relation_view')

    def test_o2m_readonly(self):
        Model = self.env['test_testing_utilities.parent']
        with Form(Model, view='test_testing_utilities.o2m_modifier') as form:
            with form.subs.new() as line:
                line.value = 5
                # this makes 'value' readonly
                line.v = 42
                with self.assertRaises(AssertionError):
                    line.value = 7

    def test_o2m_readonly_parent(self):
        Model = self.env['test_testing_utilities.parent']
        with Form(Model, view='test_testing_utilities.o2m_modifier_parent') as form:
            with form.subs.new() as line:
                line.value = 5
            # this makes 'value' readonly on lines
            form.value = 42
            with form.subs.new() as line:
                with self.assertRaises(AssertionError):
                    line.value = 7

    def test_o2m_external_readonly_parent(self):
        Model = self.env['test_testing_utilities.ref']
        with Form(Model, view='test_testing_utilities.o2m_modifier_ref') as form:
            with form.subs.new() as line:
                line.a = 1
                line.b = 2
                # readonly from context
                # with self.assertRaises(AssertionError): # this part must raise but the context attributes on x2m field is not used. To fix.
                #     line.c = 3
                # will hide 'subs' field
                form.value = 666
                with self.assertRaisesRegex(AssertionError, 'invisible'):
                    line.a = 4
                # this makes 'has_parent' readonly on lines
                form.value = 42
                line.a = 5
                with self.assertRaisesRegex(AssertionError, 'readonly'):
                    line.b = 6

    def test_o2m_widget(self):
        create = self.env['test_testing_utilities.sub'].create
        a, b, c = create({'v': 1}), create({'v': 2}), create({'v': 3})

        with Form(self.env['test_testing_utilities.parent'], view='test_testing_utilities.o2m_widget_m2m') as f:
            f.subs.add(a)
            f.subs.add(b)
            f.subs.add(c)

        r = f.record

        self.assertEqual(
            r.subs,
            a | b | c,
        )

    def test_o2m_onchange_change_saved(self):
        """ If an onchange updates o2m values (in existing sub-records of an
        existing record), those updated values should be saved, both if the
        sub-records were touched by the user and not (check that one maybe)
        """
        # create record: line created before v is updated should reflect it,
        # line created after should not
        with Form(self.env['o2m_changes_children']) as f:
            with f.line_ids.new() as line:
                line.v = 1
                line.vv = 5
            f.v = 5
            with f.line_ids.new() as line:
                ...
        r = f.record
        self.assertEqual(r.v, 5)
        self.assertEqual(r.mapped('line_ids.vv'), [5, 0])
        self.assertEqual(r.line_ids[0].v, 5, "onchange should have updated the existing lines")
        self.assertEqual(r.line_ids[1].v, 0, "onchange should not impact new line")

        # update record: onchange then touch the lines
        with Form(r) as f:
            f.v = 6
            with f.line_ids.edit(0) as line:
                line.vv = 1
            with f.line_ids.edit(1) as line:
                line.vv = 2
        self.assertEqual(r.v, 6)
        self.assertEqual(r.mapped('line_ids.vv'), [1, 2])
        self.assertEqual(r.mapped('line_ids.v'), [6, 6], "onchange should have updated vs")

        # update record: onchange then don't even touch the lines
        with Form(r) as f:
            f.v = 7
        self.assertEqual(r.v, 7)
        self.assertEqual(r.mapped('line_ids.vv'), [1, 2])
        self.assertEqual(r.mapped('line_ids.v'), [7, 7])


class TestNestedO2M(TransactionCase):
    def test_id_cannot_be_assigned(self):
        # MO with:
        # produces product0
        # produces 1 (product_qty)
        # flexible BOM produces 1
        # bom consumes 4x product 1
        # bom consumes 1x product 2
        product0 = self.env['ttu.product'].create({}).id
        product1 = self.env['ttu.product'].create({}).id
        product2 = self.env['ttu.product'].create({}).id
        # create pseudo-MO in post-asigned state
        obj = self.env['ttu.root'].create({
            'product_id': product0,
            'product_qty': 1.0,
            # qty_producing=0 (onchange)
            # qty_produced=0 (computed)
            'move_raw_ids': [
                Command.create({
                    'product_id': product2,
                    # quantity_done=0 (computed)
                    'move_line_ids': [Command.create({
                        'product_id': product2,
                        'product_uom_qty': 1.0,
                        'qty_done': 0.0,  # -> 1.0
                    })],  # -> new line with qty=0, qty_done=2
                }),
                Command.create({
                    'product_id': product1,
                    'unit_factor': 4,
                    'move_line_ids': [Command.create({
                        'product_id': product1,
                        'product_uom_qty': 4.0,
                        'qty_done': 0.0,  # -> 4.0
                    })],  # -> new line with qty=0, qty_done=8
                }),
            ],
            'move_finished_ids': [Command.create({'product_id': product0})],
            # -> new line with qty=0, qty_done=3
        })
        form = Form(obj)
        form.qty_producing = 1
        form._perform_onchange('move_raw_ids')
        form.save()

    def test_empty_update(self):
        # MO with:
        # produces product0
        # produces 1 (product_qty)
        # flexible BOM produces 1
        # bom consumes 4x product 1
        # bom consumes 1x product 2
        product0 = self.env['ttu.product'].create({}).id
        product1 = self.env['ttu.product'].create({}).id
        product2 = self.env['ttu.product'].create({}).id
        product4 = self.env['ttu.product'].create({})
        # create pseudo-MO in post-asigned state
        obj = self.env['ttu.root'].create({
            'product_id': product0,
            'product_qty': 1.0,
            # qty_producing=0 (onchange)
            # qty_produced=0 (computed)
            'move_raw_ids': [
                Command.create({
                    'product_id': product2,
                    # quantity_done=0 (computed)
                    'move_line_ids': [Command.create({
                        'product_id': product2,
                        'product_uom_qty': 1.0,
                        'qty_done': 0.0,  # -> 1.0
                    })],  # -> new line with qty=0, qty_done=2
                }),
                Command.create({
                    'product_id': product1,
                    'unit_factor': 4,
                    'move_line_ids': [Command.create({
                        'product_id': product1,
                        'product_uom_qty': 4.0,
                        'qty_done': 0.0,  # -> 4.0
                    })],  # -> new line with qty=0, qty_done=8
                }),
            ],
            'move_finished_ids': [Command.create({'product_id': product0})],
            # -> new line with qty=0, qty_done=3
        })
        form = Form(obj)
        form.qty_producing = 1
        form.save()
        with form.move_raw_ids.new() as move:
            move.product_id = product4
            move.quantity_done = 10
        # Check that this new product is not updated by qty_producing
        form.qty_producing = 2
        form.save()

    def test_remove(self):
        """ onchanges can remove o2m records which haven't been loaded yet due
        to lazy loading of o2ms. The removal information should still be
        retained, otherwise due to the stateful update system we end up
        retaining records we don't even know exist.
        """
        # create structure with sub-sub-children
        r = self.env['o2m_changes_parent'].create({
            'name': "A",
            'line_ids': [
                Command.create({
                    'name': 'line 1',
                    'v': 42,
                    'line_ids': [Command.create({'v': 1, 'vv': 1})],
                }),
            ],
        })

        with Form(r) as f:
            f.name = 'B'

        self.assertEqual(len(r.line_ids), 1)
        self.assertEqual(len(r.line_ids.line_ids), 1)
        self.assertEqual(r.line_ids.line_ids.v, 0)
        self.assertEqual(r.line_ids.line_ids.vv, 0)


class TestEdition(TransactionCase):
    """ These use the context manager form as we don't need the record
    post-save (we already have it) and it's easier to see what bits act on
    the form (inside `with`) versus outside. That let me catch a few
    mistakes.
    """
    def test_trivial(self):
        r = self.env['test_testing_utilities.a'].create({
            'f1': '5',
        })

        with Form(r) as f:
            self.assertEqual(f.id, r.id)
            self.assertEqual(f.f1, '5')
            self.assertEqual(f.f4, 8)

            f.f2 = 5
            self.assertEqual(f.f3, 2)
            self.assertEqual(f.f4, 1)

        self.assertEqual(r.f2, 5)
        self.assertEqual(r.f3, 2)

    def test_m2o(self):
        Sub = self.env['test_testing_utilities.m2o']
        a = Sub.create({'name': 'a'})
        b = Sub.create({'name': 'b'})
        c = Sub.create({'name': 'c'})

        r = self.env['test_testing_utilities.d'].create({
            'f': c.id,
            'f2': "OK",
        })

        with Form(r) as f:
            # no default/onchange should have run so loading an incoherent
            # record should still be incoherent
            self.assertEqual(f.f, c)
            self.assertEqual(f.f2, 'OK')

            f.f2 = "b"
            self.assertEqual(f.f, b)
            f.f2 = "Whoops"
            self.assertEqual(f.f, Sub)
            f.f2 = "a"
            self.assertEqual(f.f, a)

        self.assertEqual(r.f2, "a")
        self.assertEqual(r.f, a)

    def test_m2m_empty(self):
        sub = self.env['test_testing_utilities.sub2'].create({'name': 'a'})

        r = self.env['test_testing_utilities.f'].create({
            'm2m': [],
        })

        with Form(r) as f:
            f.m2o = sub

        self.assertEqual(r.m2o, sub)
        self.assertEqual(r.m2m, sub)

    def test_m2m_nonempty(self):
        Sub = self.env['test_testing_utilities.sub2']
        a = Sub.create({'name': 'a'})
        b = Sub.create({'name': 'b'})
        c = Sub.create({'name': 'c'})

        r = self.env['test_testing_utilities.f'].create({
            'm2m': [Command.set((a | b | c).ids)],
        })

        with Form(r) as f:
            self.assertEqual(f.m2m[:], (a | b | c))
            f.m2m.remove(index=0)
            self.assertEqual(f.m2m[:], (b | c))

        self.assertEqual(r.m2m, (b | c))
