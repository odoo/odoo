# -*- coding: utf-8 -*-
"""
Test for the pseudo-form implementation (odoo.tests.common.Form), which should
basically be a server-side implementation of form views (though probably not
complete) intended for properly validating business "view" flows (onchanges,
readonly, required, ...) and make it easier to generate sensible & coherent
business objects.
"""
from operator import itemgetter

from odoo.tests.common import TransactionCase, Form


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

        f.f1 = 4
        self.assertEqual(f.f2, 42)
        self.assertEqual(f.f3, 21)
        self.assertEqual(f.f4, 10)

        f.f2 = 8
        self.assertEqual(f.f3, 4)
        self.assertEqual(f.f4, 2)

        r = f.save()
        self.assertEqual(
            (r.f1, r.f2, r.f3, r.f4),
            (4, 8, 4, 2),
        )

    def test_required(self):
        f = Form(self.env['test_testing_utilities.a'])
        # f1 no default & no value => should fail
        with self.assertRaisesRegexp(AssertionError, 'f1 is a required field'):
            f.save()
        # set f1 and unset f2 => should work
        f.f1 = 1
        f.f2 = False
        r = f.save()
        self.assertEqual(
            (r.f1, r.f2, r.f3, r.f4),
            (1, 0, 0, 0)
        )

    def test_readonly(self):
        """
        Checks that fields with readonly modifiers (marked as readonly or
        computed w/o set) raise an error when set.
        """
        f = Form(self.env['test_testing_utilities.readonly'])

        with self.assertRaises(AssertionError):
            f.f1 = 5
        with self.assertRaises(AssertionError):
            f.f2 = 42

class TestM2O(TransactionCase):
    def test_default_and_onchange(self):
        """ Checks defaults & onchanges impacting m2o fields
        """
        Sub = self.env['test_testing_utilities.m2o']
        a = Sub.create({'name': "A"})
        b = Sub.create({'name': "B"})

        f = Form(self.env['test_testing_utilities.d'])

        self.assertEqual(
            f.f, a,
            "The default value for the m2o should be the first Sub record"
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
        f = Form(self.env['test_testing_utilities.e'])

        r1 = Sub.create({'name': "Item"})
        r2 = Sub.create({'name': "Item2"})

        f.m2m.add(r1)
        f.m2m.add(r2)

        r = f.save()

        self.assertEqual(
            r.m2m,
            r1 | r2
        )

    def test_remove_by_index(self):
        Sub = self.env['test_testing_utilities.sub2']
        f = Form(self.env['test_testing_utilities.e'])

        r1 = Sub.create({'name': "Item"})
        r2 = Sub.create({'name': "Item2"})

        f.m2m.add(r1)
        f.m2m.add(r2)
        f.m2m.remove(index=0)

        r = f.save()

        self.assertEqual(
            r.m2m,
            r2
        )

    def test_remove_by_id(self):
        Sub = self.env['test_testing_utilities.sub2']
        f = Form(self.env['test_testing_utilities.e'])

        r1 = Sub.create({'name': "Item"})
        r2 = Sub.create({'name': "Item2"})

        f.m2m.add(r1)
        f.m2m.add(r2)
        f.m2m.remove(id=r1.id)

        r = f.save()

        self.assertEqual(
            r.m2m,
            r2
        )

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
        Sub = self.env['test_testing_utilities.sub2']
        a = Sub.create({'name': 'a'})
        b = Sub.create({'name': 'b'})
        c = Sub.create({'name': 'c'})
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
            'm2m': [(6, 0, a.ids)]
        })

        f = Form(r)

        with self.assertRaises(AssertionError):
            f.m2m.add(b)
        with self.assertRaises(AssertionError):
            f.m2m.remove(id=a.id)

        f.save()
        self.assertEqual(r.m2m, a)


get = itemgetter('name', 'value', 'v')
class TestO2M(TransactionCase):
    def test_basic_alterations(self):
        """ Tests that the o2m proxy allows adding, removing and editing o2m
        records
        """
        f = Form(self.env['test_testing_utilities.parent'], view='test_testing_utilities.o2m_parent')

        f.subs.new().save()
        f.subs.new().save()
        f.subs.new().save()
        f.subs.remove(index=0)

        r = f.save()

        self.assertEqual(
            [get(s) for s in r.subs],
            [("2", 2, 2), ("2", 2, 2)]
        )

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

        with Form(r, view='test_testing_utilities.o2m_parent') as f, \
            f.subs.edit(index=0) as sub,\
            self.assertRaises(AssertionError):
                sub.name = "whop whop"

    def test_o2m_editable_list(self):
        """ Tests the o2m proxy when the list view is editable rather than
        delegating to a separate form view
        """
        f = Form(self.env['test_testing_utilities.parent'], view='test_testing_utilities.o2m_parent_ed')

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
        f = Form(self.env['test_testing_utilities.parent'], view='test_testing_utilities.o2m_parent_inline')

        with f.subs.new() as s:
            s.value = 42

        r = f.save()

        self.assertEqual(
            [get(s) for s in r.subs],
            [("0", 42, 0)],
            "should not have set v (and thus not name)"
        )

    def test_o2m_default(self):
        """ Tests that default_get can return defaults for the o2m
        """
        f = Form(self.env['test_testing_utilities.default'])

        with f.subs.edit(index=0) as s:
            self.assertEqual(s.v, 5)
            self.assertEqual(s.value, False)

        r = f.save()

        self.assertEqual(
            [get(s) for s in r.subs],
            [("5", 2, 5)]
        )

    def test_o2m_inner_default(self):
        """ Tests that creating an o2m record will get defaults for it
        """
        f = Form(self.env['test_testing_utilities.default'])

        with f.subs.new() as s:
            self.assertEqual(s.value, 2)
            self.assertEqual(s.v, 2, "should have onchanged value to v")

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

    def test_m2o_readonly(self):
        r = self.env['test_testing_utilities.parent'].create({
            'subs': [(0, 0, {})]
        })
        f = Form(r, view='test_testing_utilities.o2m_parent_readonly')

        with self.assertRaises(AssertionError):
            f.subs.new()
        with self.assertRaises(AssertionError):
            f.subs.edit(index=0)
        with self.assertRaises(AssertionError):
            f.subs.remove(index=0)

class TestEdition(TransactionCase):
    """ These use the context manager form as we don't need the record
    post-save (we already have it) and it's easier to see what bits act on
    the form (inside `with`) versus outside. That let me catch a few
    mistakes.
    """
    def test_trivial(self):
        r = self.env['test_testing_utilities.a'].create({
            'f1': 5,
        })

        with Form(r) as f:
            self.assertEqual(f.id, r.id)
            self.assertEqual(f.f1, 5)
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
            'm2m': [(6, 0, (a | b | c).ids)]
        })

        with Form(r) as f:
            self.assertEqual(f.m2m[:], (a | b | c))
            f.m2m.remove(index=0)
            self.assertEqual(f.m2m[:], (b | c))

        self.assertEqual(r.m2m, (b | c))
