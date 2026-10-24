from odoo.tests import TransactionCase


class TestResourceResource(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.michel, cls.daniel = cls.env['res.users'].create([
            {'name': 'Michel', 'login': 'michel@mail.com', 'password': 'michel@mail.com'},
            {'name': 'Daniel', 'login': 'daniel@mail.com', 'password': 'daniel@mail.com'},
        ])

        (
            cls.resource_claudy,
            cls.resource_dominique,
            cls.resource_michel,
            cls.resource_michel_michel,
            cls.resource_daniel_1,
            cls.resource_daniel_2,
        ) = cls.env['resource.resource'].create([
            {'name': 'Claudy'},
            {'name': 'Dominique'},
            {'name': 'Michel', 'user_id': cls.michel.id},
            {'name': 'Michel Michel'},
            {'name': 'Daniel 1', 'user_id': cls.daniel.id},
            {'name': 'Daniel 2', 'user_id': cls.daniel.id},
        ])
        cls.resources = cls.resource_claudy + cls.resource_dominique + cls.resource_michel + cls.resource_michel_michel + cls.resource_daniel_1 + cls.resource_daniel_2

    def test_name_search(self):
        """ Test that `name_search` returns the current user's resources first. """
        ResourceResource = self.env['resource.resource']
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.michel).name_search(name='', domain=[('id', 'in', self.resources.ids)])]
        self.assertEqual(self.resource_michel.id, resource_ids[0], "The current user's resource, Michel, should be the first in the result.")
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.michel).name_search(name='Claudy', domain=[('id', 'in', self.resources.ids)])]
        self.assertNotIn(self.resource_michel.id, resource_ids, "The current user's resource, Michel, should not be in the result because its name does not fit the condition.")

        daniel_resource_ids = (self.resource_daniel_1 | self.resource_daniel_2).ids
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.daniel).name_search(name='', domain=[('id', 'in', self.resources.ids)], limit=3)]
        self.assertCountEqual(daniel_resource_ids, resource_ids[:2], "Both resources of the current user, Daniel, should be the first in the result.")
        self.assertEqual(len(resource_ids), 3, "The number of results found should still respect the limit set.")
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.daniel).name_search(name='Daniel', domain=[('id', 'in', self.resources.ids)], limit=1)]
        self.assertEqual(len(resource_ids), 1, "The number of results found should still respect the limit set.")
        self.assertIn(resource_ids[0], daniel_resource_ids, "A resource of the current user, Daniel, should be the only result.")
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.daniel).name_search(name='a', domain=[('id', 'in', self.resources.ids)], limit=1)]
        self.assertEqual(len(resource_ids), 1, "The number of results found should still respect the limit set.")
        self.assertEqual(resource_ids[0], self.resource_daniel_1.id, "The current user's resource, Daniel, should be the only result.")
        self.assertNotIn(self.resource_claudy.id, resource_ids, "Other resources matching the search, i.e., Claudy, should not be in the result.")
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.daniel).name_search(name='', domain=[('id', 'in', self.resources.ids)], limit=5)]
        self.assertEqual(
            resource_ids,
            [self.resource_daniel_1.id, self.resource_daniel_2.id, self.resource_claudy.id, self.resource_dominique.id, self.resource_michel.id],
            "The current user's resources found should come first, then the ones fetched again, then the other ones.",
        )
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.daniel).name_search(name='', domain=[('id', 'in', self.resources.ids)])]
        self.assertEqual(len(resource_ids), len(set(resource_ids)), "Some resource(s), appear multiple times in the result")
