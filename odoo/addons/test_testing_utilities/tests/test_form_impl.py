# -*- coding: utf-8 -*-
"""
Test for the pseudo-form implementation (odoo.tests.Form), which should
basically be a server-side implementation of form views (though probably not
complete) intended for properly validating business "view" flows (onchanges,
readonly, required, ...) and make it easier to generate sensible & coherent
business objects.
"""
from lxml import etree
from operator import itemgetter

from odoo.tests import TransactionCase, Form
from odoo import Command


class TestBasic(TransactionCase):
    def test_defaults(self):
        """
        Checks that we can load a default form view and perform trivial
        default_get & onchanges & computations
        """
        f = Form(self.env['test_testing_utilities.a'])
        self.assertEqual(f.id, False, "check that our record is not in db (yet)")

        self.assertEqual(f.f2, 42)
        self.assertEqual(f.f3, 21)
        self.assertEqual(f.f4, 42)

        f.f1 = '4'
        self.assertEqual(f.f2, 42)
        self.assertEqual(f.f3, 21)
        self.assertEqual(f.f4, 10)

        f.f2 = 8
        self.assertEqual(f.f3, 4)
        self.assertEqual(f.f4, 2)

        # f.record cannot be accessed yet
        with self.assertRaises(AssertionError):
            f.record

        r = f.save()
        self.assertEqual(
            (r.f1, r.f2, r.f3, r.f4),
            ('4', 8, 4, 2),
        )
        self.assertEqual(f.record, r)

    def test_required(self):
        f = Form(self.env['test_testing_utilities.a'])
        # f1 no default & no value => should fail
        with self.assertRaisesRegex(AssertionError, 'f1 is a required field'):
            f.save()
        # set f1 and unset f2 => should work
        f.f1 = '1'
        f.f2 = False
        r = f.save()
        self.assertEqual(
            (r.f1, r.f2, r.f3, r.f4),
            ('1', 0, 0, 0)
        )

    def test_required_bool(self):
        f = Form(self.env['test_testing_utilities.req_bool'])
        f.f_bool = False
        r = f.save()
        self.assertEqual(r.f_bool, 0)

        f2 = Form(self.env['test_testing_utilities.req_bool'])
        r2 = f2.save()
        self.assertEqual(r2.f_bool, 0)

    def test_readonly(self):
        """
        Checks that fields with readonly modifiers (marked as readonly or
        computed w/o set) raise an error when set.
        """
        f = Form(self.env['test_testing_utilities.readonly'])

        with self.assertRaises(AssertionError):
            f.f1 = '5'
        with self.assertRaises(AssertionError):
            f.f2 = 42

    def test_readonly_save(self):
        """ Should not save readonly fields unless they're force_save
        """
        f = Form(self.env['test_testing_utilities.a'], view='test_testing_utilities.non_normalized_attrs')

        f.f1 = '1'
        f.f2 = 987
        self.assertEqual(f.f5, 987)
        self.assertEqual(f.f6, 987)
        r = f.save()
        self.assertEqual(r.f5, 0)
        self.assertEqual(r.f6, 987)

    def test_attrs(self):
        """ Checks that attrs/modifiers with non-normalized domains work
        """
        f = Form(self.env['test_testing_utilities.a'], view='test_testing_utilities.non_normalized_attrs')

        # not readonly yet, should work
        f.f2 = 5
        # make f2 readonly
        f.f1 = '63'
        f.f3 = 5
        with self.assertRaises(AssertionError):
            f.f2 = 6

class TestM2O(TransactionCase):
    def test_default_and_onchange(self):
        """ Checks defaults & onchanges impacting m2o fields
        """
        Sub = self.env['test_testing_utilities.m2o']
        a = Sub.create({'name': "A"})
        b = Sub.create({'name': "B"})

        f = Form(self.env['test_testing_utilities.d'])

        self.assertFalse(
            f.f,
            "The default value gets overridden by the onchange"
        )
        f.f2 = "B"
        self.assertEqual(
            f.f, b,
            "The new m2o value should match the second field by name"
        )

        f.save()

    def test_set(self):
        """
        Checks that we get/set recordsets for m2o & that set correctly
        triggers onchange
        """
        r1 = self.env['test_testing_utilities.m2o'].create({'name': "A"})
        r2 = self.env['test_testing_utilities.m2o'].create({'name': "B"})

        f = Form(self.env['test_testing_utilities.c'])

        # check that basic manipulations work
        f.f2 = r1
        self.assertEqual(f.f2, r1)
        self.assertEqual(f.name, 'A')
        f.f2 = r2
        self.assertEqual(f.name, 'B')

        # can't set an int to an m2o field
        with self.assertRaises(AssertionError):
            f.f2 = r1.id
        self.assertEqual(f.f2, r2)
        self.assertEqual(f.name, 'B')

        # can't set a record of the wrong model
        temp = self.env['test_testing_utilities.readonly'].create({})
        with self.assertRaises(AssertionError):
            f.f2 = temp
        self.assertEqual(f.f2, r2)
        self.assertEqual(f.name, 'B')

        r = f.save()
        self.assertEqual(r.f2, r2)

class TestM2M(TransactionCase):
    def test_add(self):
        Sub = self.env['test_testing_utilities.sub2']
        r1 = Sub.create({'name': "Item"})
        r2 = Sub.create({'name': "Item2"})

        with Form(self.env['test_testing_utilities.e']) as f:
            f.m2m.add(r1)
            f.m2m.add(r2)

        self.assertEqual(
            f.record.m2m,
            r1 | r2
        )

    def test_remove_by_index(self):
        Sub = self.env['test_testing_utilities.sub2']
        r1 = Sub.create({'name': "Item"})
        r2 = Sub.create({'name': "Item2"})

        with Form(self.env['test_testing_utilities.e']) as f:
            f.m2m.add(r1)
            f.m2m.add(r2)
            f.m2m.remove(index=0)

        self.assertEqual(
            f.record.m2m,
            r2
        )

    def test_remove_by_id(self):
        Sub = self.env['test_testing_utilities.sub2']
        r1 = Sub.create({'name': "Item"})
        r2 = Sub.create({'name': "Item2"})

        with Form(self.env['test_testing_utilities.e']) as f:
            f.m2m.add(r1)
            f.m2m.add(r2)
            f.m2m.remove(id=r1.id)

        self.assertEqual(
            f.record.m2m,
            r2
        )

    def test_set(self):
        Sub = self.env['test_testing_utilities.sub2']
        r1 = Sub.create({'name': "Item"})
        r2 = Sub.create({'name': "Item2"})
        r3 = Sub.create({'name': "Item3"})

        with Form(self.env['test_testing_utilities.e']) as f:
            f.m2m.set(r1 + r2)

        self.assertEqual(f.record.m2m, r1 + r2)

        with f:
            f.m2m = r3

        self.assertEqual(f.record.m2m, r3)

    def test_on_m2m_change(self):
        Sub = self.env['test_testing_utilities.sub2']
        f = Form(self.env['test_testing_utilities.e'])

        self.assertEqual(f.count, 0)
        f.m2m.add(Sub.create({'name': 'a'}))
        self.assertEqual(f.count, 1)
        f.m2m.add(Sub.create({'name': 'a'}))
        f.m2m.add(Sub.create({'name': 'a'}))
        f.m2m.add(Sub.create({'name': 'a'}))
        self.assertEqual(f.count, 4)
        f.m2m.remove(index=0)
        f.m2m.remove(index=0)
        f.m2m.remove(index=0)
        self.assertEqual(f.count, 1)

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

    def test_m2m_readonly(self):
        Sub = self.env['test_testing_utilities.sub3']
        a = Sub.create({'name': 'a'})
        b = Sub.create({'name': 'b'})
        r = self.env['test_testing_utilities.g'].create({
            'm2m': [Command.set(a.ids)]
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
            ['ok', '1', '2', '3', '4']
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
            [("2", 2, 2), ("2", 2, 2)]
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
            [("2", 2, 2), ("5", 5, 5), ("2", 2, 2)]
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
            'check that the list view is the one referenced by list_view_ref'
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
            [('1', 1, 1), ('3', 3, 3), ('7', 7, 7)]
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
            "should not have set v (and thus not name)"
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
            [("5", 2, 5)]
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
            'subs': [Command.create({})]
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
            ('ok', 2)
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
            a | b | c
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
        self.assertEqual(r.line_ids.mapped('vv'), [5, 0])
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
        self.assertEqual(r.line_ids.mapped('vv'), [1, 2])
        self.assertEqual(r.line_ids.mapped('v'), [6, 6], "onchange should have updated vs")

        # update record: onchange then don't even touch the lines
        with Form(r) as f:
            f.v = 7
        self.assertEqual(r.v, 7)
        self.assertEqual(r.line_ids.mapped('vv'), [1, 2])
        self.assertEqual(r.line_ids.mapped('v'), [7, 7])

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
                        'qty_done': 0.0 # -> 1.0
                    })] # -> new line with qty=0, qty_done=2
                }),
                Command.create({
                    'product_id': product1,
                    'unit_factor': 4,
                    'move_line_ids': [Command.create({
                        'product_id': product1,
                        'product_uom_qty': 4.0,
                        'qty_done': 0.0 # -> 4.0
                    })] # -> new line with qty=0, qty_done=8
                })
            ],
            'move_finished_ids': [Command.create({'product_id': product0})]
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
                        'qty_done': 0.0 # -> 1.0
                    })] # -> new line with qty=0, qty_done=2
                }),
                Command.create({
                    'product_id': product1,
                    'unit_factor': 4,
                    'move_line_ids': [Command.create({
                        'product_id': product1,
                        'product_uom_qty': 4.0,
                        'qty_done': 0.0 # -> 4.0
                    })] # -> new line with qty=0, qty_done=8
                })
            ],
            'move_finished_ids': [Command.create({'product_id': product0})]
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
                })
            ]
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
            'm2m': []
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
            'm2m': [Command.set((a | b | c).ids)]
        })

        with Form(r) as f:
            self.assertEqual(f.m2m[:], (a | b | c))
            f.m2m.remove(index=0)
            self.assertEqual(f.m2m[:], (b | c))

        self.assertEqual(r.m2m, (b | c))
