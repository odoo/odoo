# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class TestHierarchyRead(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.albert = Partner.create({'name': 'Albert', 'is_company': True})
        cls.georges = Partner.create({'name': 'Georges', 'parent_id': cls.albert.id})
        cls.josephine = Partner.create({'name': 'Josephine', 'parent_id': cls.albert.id})
        cls.louis = Partner.create({'name': 'Louis', 'parent_id': cls.josephine.id})
        cls.partners = cls.albert | cls.georges | cls.josephine | cls.louis

    def hierarchy_read(self, partners, **kwargs):
        return self.env['res.partner'].hierarchy_read(
            [('id', 'in', partners.ids)], {'name': {}}, 'parent_id', **kwargs,
        )

    def assertHierarchy(self, result, children, length):
        """ Checks the structure of a result of ``hierarchy_read``, and that its records
        are the displayed children, in breadth-first order. """
        self.assertEqual(result['children'], [
            (parent.id, child_records.ids) for parent, child_records in children
        ])
        self.assertEqual(
            [record['name'] for record in result['records']],
            [name for __, child_records in children for name in child_records.mapped('name')],
        )
        self.assertEqual(result['length'], length)

    def test_trees(self):
        result = self.hierarchy_read(self.partners)
        self.assertHierarchy(result, [
            (self.env['res.partner'], self.albert),
            (self.albert, self.josephine + self.georges),
            (self.josephine, self.louis),
        ], length=4)

    def test_children_sorted_by_children_count(self):
        """ The children of a record are sorted by decreasing number of children. """
        Partner = self.env['res.partner']
        paul = Partner.create({'name': 'Paul', 'parent_id': self.georges.id})
        marie = Partner.create({'name': 'Marie', 'parent_id': self.georges.id})
        result = self.hierarchy_read(self.partners | paul | marie)
        self.assertHierarchy(result, [
            (Partner, self.albert),
            (self.albert, self.georges + self.josephine),
            (self.georges, marie + paul),
            (self.josephine, self.louis),
        ], length=6)

    def test_parent_not_matching_the_domain(self):
        """ A record whose parent does not match the domain is a root. """
        result = self.hierarchy_read(self.partners - self.josephine)
        self.assertHierarchy(result, [
            (self.env['res.partner'], self.albert | self.louis),
            (self.albert, self.georges),
        ], length=3)

    def test_limit_breadth_first(self):
        """ The levels are loaded one after the other: the children of a record are
        loaded only once all the records of its level are. """
        result = self.hierarchy_read(self.partners, limit=3)
        self.assertHierarchy(result, [
            (self.env['res.partner'], self.albert),
            (self.albert, self.josephine + self.georges),
        ], length=4)

        result = self.hierarchy_read(self.partners, limit=2)
        self.assertHierarchy(result, [
            (self.env['res.partner'], self.albert),
            (self.albert, self.josephine),
        ], length=4)

    def test_cycles(self):
        """ A record which is its own parent is a root, and a cycle is broken on its
        first record: each record is loaded once. """
        # the constraints of res.partner prevent cycles: bypass them
        self.env.cr.execute("UPDATE res_partner SET parent_id = %s WHERE id = %s", [self.louis.id, self.albert.id])
        self.env.cr.execute("UPDATE res_partner SET parent_id = %s WHERE id = %s", [self.georges.id, self.georges.id])
        self.env['res.partner'].invalidate_model(['parent_id'])

        result = self.hierarchy_read(self.partners)
        self.assertHierarchy(result, [
            (self.env['res.partner'], self.albert + self.georges),
            (self.albert, self.josephine),
            (self.josephine, self.louis),
        ], length=4)

    def test_no_record(self):
        result = self.hierarchy_read(self.env['res.partner'])
        self.assertEqual(result, {'records': [], 'length': 0, 'children': []})

    def test_invalid_parent_field(self):
        Partner = self.env['res.partner']
        for parent_field_name in ('unknown_field', 'name', 'country_id'):
            with self.subTest(parent_field_name=parent_field_name), self.assertRaises(ValueError):
                Partner.hierarchy_read([], {'name': {}}, parent_field_name)
