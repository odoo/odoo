from odoo.tests import TransactionCase, tagged


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResourceResource(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.jean, cls.pascal = cls.env['res.users'].create([
            {'name': 'Jean', 'login': 'jean@mail.com', 'password': 'jean@mail.com'},
            {'name': 'Pascal', 'login': 'pascal@mail.com', 'password': 'pascal@mail.com'},
        ])

        (
            cls.resource_claude,
            cls.resource_georges,
            cls.resource_jean,
            cls.resource_jean_paul,
            cls.resource_pascal_be,
            cls.resource_pascal_fr,
        ) = cls.env['resource.resource'].create([
            {'name': 'Claude'},
            {'name': 'Georges'},
            {'name': 'Jean', 'user_id': cls.jean.id},
            {'name': 'Jean-Paul'},
            {'name': 'Pascal (BE)', 'user_id': cls.pascal.id},
            {'name': 'Pascal (FR)', 'user_id': cls.pascal.id},
        ])

    def test_name_search(self):
        """
        Test name search with self assign feature
        The self assign feature is present only when a limit is present,
        which is the case with the public name_search by default
        """
        ResourceResource = self.env['resource.resource']
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.jean).name_search('')]
        self.assertEqual(self.resource_jean.id, resource_ids[0], "The current user's resource, Jean, should be the first in the result.")
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.jean).name_search('Claude')]
        self.assertNotIn(self.resource_jean.id, resource_ids, "The current user's resource, Jean, should not be in the result because its name does not fit the condition.")

        pascal_resource_ids = (self.resource_pascal_be | self.resource_pascal_fr).ids
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.pascal).name_search('', limit=3)]
        self.assertCountEqual(pascal_resource_ids, resource_ids[:2], "Both resources of the current user, Pascal, should be the first in the result.")
        self.assertEqual(len(resource_ids), 3, "The number of results found should still respect the limit set.")
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.pascal).name_search('Pascal', limit=1)]
        self.assertEqual(len(resource_ids), 1, "The number of results found should still respect the limit set.")
        self.assertIn(resource_ids[0], pascal_resource_ids, "A resource of the current user, Pascal, should be the only result.")
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.pascal).name_search('', limit=5)]
        self.assertEqual(
            resource_ids,
            [self.resource_pascal_be.id, self.resource_pascal_fr.id, self.resource_claude.id, self.resource_georges.id, self.resource_jean.id],
            "The current user's resources found should come first, then the ones fetched again, then the other ones.",
        )
        resource_ids = [id_ for id_, __ in ResourceResource.with_user(self.pascal).name_search('')]
        self.assertEqual(len(resource_ids), len(set(resource_ids)), "Some resource(s), appear multiple times in the result")
