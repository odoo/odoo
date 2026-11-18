# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, new_test_user


class TestHierarchyRead(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.root = Partner.create({'name': 'Root', 'is_company': True})
        cls.child_a = Partner.create({'name': 'A', 'parent_id': cls.root.id})
        cls.child_b = Partner.create({'name': 'B', 'parent_id': cls.root.id})
        cls.grandchild = Partner.create({'name': 'A1', 'parent_id': cls.child_a.id})
        cls.all_partners = cls.root + cls.child_a + cls.child_b + cls.grandchild
        cls.specification = {
            'name': {},
            'parent_id': {'fields': {'display_name': {}}},
        }

    def _hierarchy_read(self, domain, model=None, **kwargs):
        model = model if model is not None else self.env['res.partner']
        domain = [('id', 'in', self.all_partners.ids), *domain]
        return model.hierarchy_read(domain, self.specification, 'parent_id', order='id', **kwargs)

    def _ids(self, result):
        return [values['id'] for values in result['records']]

    # ------------------------------------------------------------------
    # Target parent from the domain
    # ------------------------------------------------------------------

    def test_target_parent_from_domain(self):
        result = self._hierarchy_read([('parent_id', '=', self.root.id)])
        self.assertEqual(result['parent']['id'], self.root.id)
        self.assertEqual(result['parent']['name'], 'Root')
        self.assertEqual(self._ids(result), (self.child_a + self.child_b).ids)
        self.assertEqual(result['length'], 2)

    def test_target_parent_without_children(self):
        result = self._hierarchy_read([('parent_id', '=', self.child_b.id)])
        self.assertEqual(result['parent']['id'], self.child_b.id, "the parent is read even without children")
        self.assertEqual(result['records'], [])
        self.assertEqual(result['length'], 0)

    def test_target_parent_out_of_page(self):
        result = self._hierarchy_read([('parent_id', '=', self.root.id)], offset=5, limit=1)
        self.assertEqual(result['parent']['id'], self.root.id)
        self.assertEqual(result['records'], [])

    def test_target_parent_pagination(self):
        result = self._hierarchy_read([('parent_id', '=', self.root.id)], offset=1, limit=1)
        self.assertEqual(result['parent']['id'], self.root.id)
        self.assertEqual(self._ids(result), self.child_b.ids)
        self.assertEqual(result['length'], 2, "the parent is not counted in the length")

    def test_target_parent_condition_not_at_first_level(self):
        """ A condition on the parent field under a OR does not restrict the
        records, so it must not be considered as a target. """
        result = self._hierarchy_read([
            '|', ('parent_id', '=', self.root.id), ('id', '=', self.grandchild.id),
        ])
        self.assertFalse(result['parent'])
        self.assertEqual(self._ids(result), (self.child_a + self.child_b + self.grandchild).ids)

    def test_target_parent_other_operator(self):
        result = self._hierarchy_read([('parent_id', 'in', [self.root.id])])
        self.assertFalse(result['parent'], "only the '=' operator defines a target")

    def test_target_parent_not_accessible(self):
        user = new_test_user(self.env, login='hierarchy_user', groups='base.group_user')
        self.env['ir.access'].create({
            'name': 'Hide the root partner',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'operation': 'r',
            'domain': [('id', '!=', self.root.id)],
        })
        result = self._hierarchy_read(
            [('parent_id', '=', self.root.id)],
            model=self.env['res.partner'].with_user(user),
        )
        self.assertFalse(result['parent'], "an inaccessible parent is not returned")
        self.assertEqual(self._ids(result), (self.child_a + self.child_b).ids)

    # ------------------------------------------------------------------
    # Roots only
    # ------------------------------------------------------------------

    def test_roots_only_single_root_is_unfolded(self):
        result = self._hierarchy_read([], roots_only=True)
        self.assertEqual(result['parent']['id'], self.root.id)
        self.assertEqual(self._ids(result), (self.child_a + self.child_b).ids)
        self.assertEqual(result['length'], 2)

    def test_roots_only_several_roots(self):
        other_root = self.env['res.partner'].create({'name': 'Other root', 'is_company': True})
        self.all_partners += other_root
        result = self._hierarchy_read([], roots_only=True)
        self.assertFalse(result['parent'])
        self.assertEqual(self._ids(result), (self.root + other_root).ids)
        self.assertEqual(result['length'], 2)

    def test_roots_only_without_roots(self):
        result = self._hierarchy_read([('id', '!=', self.root.id)], roots_only=True)
        self.assertFalse(result['parent'])
        self.assertEqual(result['records'], [])
        self.assertEqual(result['length'], 0)

    def test_roots_only_single_root_unfolded_with_limit_1(self):
        """ The size of the page doesn't change the display mode: a single
        root is unfolded, and the page applies to its children. """
        result = self._hierarchy_read([], roots_only=True, limit=1)
        self.assertEqual(result['parent']['id'], self.root.id)
        self.assertEqual(self._ids(result), self.child_a.ids)
        self.assertEqual(result['length'], 2)

    def test_roots_only_several_roots_next_page(self):
        """ On the next pages, the page still applies to the roots when there
        are several of them. """
        other_root = self.env['res.partner'].create({'name': 'Other root', 'is_company': True})
        self.all_partners += other_root
        result = self._hierarchy_read([], roots_only=True, offset=1, limit=1)
        self.assertFalse(result['parent'])
        self.assertEqual(self._ids(result), other_root.ids)
        self.assertEqual(result['length'], 2)

    def test_roots_only_single_root_children_pagination(self):
        """ The next pages of the children of the unfolded root must still
        contain the root as parent. """
        result = self._hierarchy_read([], roots_only=True, offset=1, limit=1)
        self.assertEqual(result['parent']['id'], self.root.id)
        self.assertEqual(self._ids(result), self.child_b.ids)
        self.assertEqual(result['length'], 2)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def test_search_is_not_restricted_to_roots(self):
        result = self._hierarchy_read([('name', 'in', ['A', 'A1'])])
        self.assertFalse(result['parent'])
        self.assertEqual(self._ids(result), (self.child_a + self.grandchild).ids)
        self.assertEqual(result['length'], 2)

    def test_search_single_result_is_not_unfolded(self):
        result = self._hierarchy_read([('name', '=', 'A')])
        self.assertFalse(result['parent'])
        self.assertEqual(self._ids(result), self.child_a.ids)
