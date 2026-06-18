from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo.tools.constants import PREFETCH_MAX

from .common import TestOrmPartnerCommon
from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


@tagged('at_install', '-post_install')
class TestPrefecth(TestOrmPartnerCommon, SavepointCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._load_partners_set()

    @mute_logger('odoo.models')
    def test_prefetch_model(self):
        partners = self.partners
        self.assertGreater(len(partners), 5)

        prefetch_ids = partners._prefetch_ids
        self.assertTrue(prefetch_ids)
        self.assertIsInstance(prefetch_ids, tuple)

        # The recordset operations below use different prefetch sets
        partners_subset = partners.browse(partners.ids[:5])
        self.assertNotEqual(prefetch_ids, partners.browse()._prefetch_ids)
        self.assertNotEqual(prefetch_ids, partners_subset._prefetch_ids)

        # The recordset operations below share the prefetch set
        self.assertEqual(prefetch_ids, partners.browse(partners.ids)._prefetch_ids)
        self.assertEqual(prefetch_ids, partners.with_user(self.user_demo)._prefetch_ids)
        self.assertEqual(prefetch_ids, partners.with_context(active_test=False)._prefetch_ids)
        self.assertEqual(prefetch_ids, partners_subset.with_prefetch(prefetch_ids)._prefetch_ids)
        self.assertEqual(set(prefetch_ids), set(partners.filtered('country_id')._prefetch_ids))
        self.assertEqual(prefetch_ids, partners[0]._prefetch_ids)
        self.assertEqual(set(prefetch_ids), set(partners[:5]._prefetch_ids))

    @mute_logger('odoo.models')
    def test_prefetch_model_relational_fields(self):
        empty_relational_fields = {
            'name': 'Empty relational fields',
            'country_id': False,
            'user_ids': [],
            'category_id': [],
        }
        non_empty_relational_fields = {
            'name': 'Non-empty relational fields',
            'country_id': self.country_be.id,
            'user_ids': [Command.create({'name': 'FOO42'})],
            'category_id': [Command.link(self.partner_category.id)],
        }

        partners = self.env['test_orm.partner'].create([empty_relational_fields, non_empty_relational_fields])
        self.assertEqual(type(partners).country_id.type, 'many2one')
        self.assertEqual(type(partners).user_ids.type, 'one2many')
        self.assertEqual(type(partners).category_id.type, 'many2many')

        # Iteration and relational fields should use the same prefetch set
        for partner in partners:
            self.assertEqual(partner._prefetch_ids, partners._prefetch_ids)
            self.assertEqual(set(partner.country_id._prefetch_ids), set(partners.country_id._prefetch_ids))
            self.assertEqual(set(partner.user_ids._prefetch_ids), set(partners.user_ids._prefetch_ids))
            self.assertEqual(set(partner.category_id._prefetch_ids), set(partners.category_id._prefetch_ids))

    @mute_logger('odoo.models')
    def test_prefetch_model_operations(self):
        # Records concatenation, union, intersection, difference
        partners = self.partners
        prefetch_ids = partners._prefetch_ids
        part = partners.browse(partners.ids[:5])
        ners = partners.browse(partners.ids[5:])
        self.assertNotEqual(part._prefetch_ids, ners._prefetch_ids)

        self.assertEqual(set(prefetch_ids), set((partners & ners)._prefetch_ids))
        self.assertEqual(set(prefetch_ids), set((partners - ners)._prefetch_ids))

        # Those are not the same prefetch object, but they return the same ids
        self.assertNotEqual(prefetch_ids, (part + ners)._prefetch_ids)
        self.assertNotEqual(prefetch_ids, (part | ners)._prefetch_ids)
        self.assertEqual(set(prefetch_ids), set((part + ners)._prefetch_ids))
        self.assertEqual(set(prefetch_ids), set((part | ners)._prefetch_ids))

        # Combining concatenation and union with relational fields
        child_ids = partners.child_ids._ids
        self.assertEqual(set(child_ids), set(partners.child_ids._prefetch_ids))
        self.assertEqual(set(child_ids), set((part.child_ids + ners.child_ids)._prefetch_ids))
        self.assertEqual(set(child_ids), set((part.child_ids | ners.child_ids)._prefetch_ids))

        prefetch_ids = partners.child_ids._prefetch_ids
        children = [partner.child_ids[:1] for partner in partners]

        for child in children:
            self.assertEqual(set(prefetch_ids), set(child._prefetch_ids))

        self.assertEqual(set(prefetch_ids), set(partners.browse().concat(children)._prefetch_ids))
        self.assertEqual(set(prefetch_ids), set(partners.browse().union(children)._prefetch_ids))

    def test_prefetch_model_performance(self):
        # number of records, and number of children per record
        RECORDS = PREFETCH_MAX
        CHILDREN = 7

        country = self.env['test_orm.country'].create({'name': 'Belgium'}).id
        partners = self.env['test_orm.partner'].create([{
            'name': f'Partner {i}',
            'child_ids': [
                Command.create({'name': f'Child {i} {j}', 'country_id': country})
                for j in range(CHILDREN)],
        } for i in range(RECORDS)
        ])

        with self.subTest("Prefetch size"):
            # incremental concatenation/union should not cause a recursion error
            result = partners.browse()
            for partner in partners:
                result += partner.with_prefetch()
            main_size = RECORDS * 2  # current ids + prefetched ids
            self.assertEqual(len(list(result._prefetch_ids)), main_size)

            # get the children
            children = partners[0].child_ids
            main_size = RECORDS * CHILDREN  # total number of children
            self.assertEqual(len(list(children._prefetch_ids)), main_size)

            # union with all children
            children |= children.parent_id.child_ids
            main_size *= 2  # because PrefetchUnion has both prefetch and ids
            self.assertEqual(len(list(children._prefetch_ids)), main_size + CHILDREN)

            # now incrementally build
            result = partners.browse()
            for child in children:
                result += child
            self.assertEqual(len(list(result._prefetch_ids)), main_size + CHILDREN)

            # country of first child (harder case)
            result = partners.country_id.browse()
            for partner in partners[:11]:
                result += partner.child_ids[0].country_id
            main_size = RECORDS * CHILDREN + 11
            self.assertEqual(len(list(result._prefetch_ids)), main_size)

        # when building subsets of large recordsets, prefetch in priority the
        # records in the subset
        with self.subTest("Prefetch priority"):
            children = partners.child_ids.with_prefetch()

            records = children.filtered(lambda child: child.name.endswith('1'))
            records.invalidate_model(['name'])
            records.mapped('name')
            fetched_ids = records._fields['name']._get_all_cache_ids(records.env)
            self.assertTrue(set(records._ids).issubset(set(fetched_ids)))
            self.assertEqual(set(records._prefetch_ids), set(fetched_ids))

            records = children[500 : RECORDS + 500]
            records.invalidate_model(['name'])
            records.mapped('name')
            fetched_ids = records._fields['name']._get_all_cache_ids(records.env)
            self.assertTrue(set(records._ids).issubset(set(fetched_ids)))
            self.assertEqual(set(records._prefetch_ids), set(fetched_ids))

            records = children - children[500 : RECORDS + 500]
            records.invalidate_model(['name'])
            records.mapped('name')
            fetched_ids = records._fields['name']._get_all_cache_ids(records.env)
            self.assertTrue(set(records._ids).issubset(set(fetched_ids)))
            self.assertEqual(set(records._prefetch_ids), set(fetched_ids))

            records = self.env['test_orm.partner'].concat(partner.child_ids[0] for partner in partners)
            records.invalidate_model(['name'])
            records.mapped('name')
            fetched_ids = records._fields['name']._get_all_cache_ids(records.env)
            self.assertTrue(set(records._ids).issubset(set(fetched_ids)))
            self.assertEqual(set(records._prefetch_ids), set(fetched_ids))

    @mute_logger('odoo.models')
    def test_prefetch_read_compute(self):
        field = self.env['test_orm.partner']._fields['vat']
        self.assertTrue(field.compute and not field.store)

        partner_parent = self.partners.filtered_domain([('name', 'ilike', 'Amber & Forge')])
        partner_child = partner_parent.child_ids
        self.assertEqual(partner_parent.child_ids, partner_child)

        self.env.transaction.clear()
        partner_parent = partner_parent.with_prefetch()
        partner_parent.read(['vat'])
        self.assertIn('vat', partner_parent._cache)
        self.assertNotIn('vat', partner_child._cache)

        self.env.transaction.clear()
        partner_parent = partner_parent.with_prefetch()
        partner_parent.read(['child_ids', 'vat'])
        self.assertIn('vat', partner_parent._cache)
        self.assertNotIn('vat', partner_child._cache)
