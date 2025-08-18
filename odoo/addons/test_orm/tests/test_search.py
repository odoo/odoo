from odoo.addons.base.tests.test_expression import TransactionExpressionCase
from odoo.fields import Command, Domain
from odoo.tests import TransactionCase


class TestSubqueries(TransactionCase):
    """ Test the subqueries made by search() with relational fields. """
    maxDiff = None

    def test_and_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE "test_orm_multi"."partner" IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE ("res_partner"."name" LIKE %s
                   AND "res_partner"."phone" LIKE %s
                )
            )
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                ('partner.name', 'like', 'jack'),
                ('partner.phone', 'like', '01234'),
            ])

    def test_or_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE "test_orm_multi"."partner" IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE ("res_partner"."name" LIKE %s
                    OR "res_partner"."phone" LIKE %s
                )
            )
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                '|',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_not_and_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE ("test_orm_multi"."partner" NOT IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE ("res_partner"."name" LIKE %s
                    AND "res_partner"."phone" LIKE %s
                )
            ) OR "test_orm_multi"."partner" IS NULL)
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                '!', '&',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_not_or_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE ("test_orm_multi"."partner" NOT IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE ("res_partner"."name" LIKE %s
                    OR "res_partner"."phone" LIKE %s
                )
            ) OR "test_orm_multi"."partner" IS NULL)
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                '!', '|',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_or_bypass_access_many2one_with_subfield(self):
        self.patch(self.env['test_orm.multi']._fields['partner'], 'bypass_search_access', True)
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            LEFT JOIN "res_partner" AS "test_orm_multi__partner"
                ON ("test_orm_multi"."partner" = "test_orm_multi__partner"."id")
            WHERE ("test_orm_multi"."partner" IS NOT NULL AND (
                "test_orm_multi__partner"."name" LIKE %s
                OR "test_orm_multi__partner"."phone" LIKE %s
            ))
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                '|',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_not_or_bypass_access_many2one_with_subfield(self):
        self.patch(self.env['test_orm.multi']._fields['partner'], 'bypass_search_access', True)
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            LEFT JOIN "res_partner" AS "test_orm_multi__partner"
                ON ("test_orm_multi"."partner" = "test_orm_multi__partner"."id")
            WHERE (
                "test_orm_multi"."partner" IS NULL OR
                ((
                    "test_orm_multi__partner"."name" LIKE %s
                    OR "test_orm_multi__partner"."phone" LIKE %s
                )) IS NOT TRUE
            )
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                '!', '|',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_mixed_and_or_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE "test_orm_multi"."partner" IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE (
                    "res_partner"."email" LIKE %s
                    AND ("res_partner"."name" LIKE %s
                      OR "res_partner"."phone" LIKE %s
                    )
                )
            )
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                ('partner.email', 'like', '@sgc.us'),
                '|',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_mixed_and_or_not_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE (
                {many2one} IN (
                    {subselect}
                    WHERE (
                        "res_partner"."email" LIKE %s
                        OR "res_partner"."name" LIKE %s
                    )
                )
                AND ({many2one} NOT IN (
                    {subselect}
                    WHERE "res_partner"."website" LIKE %s
                ) OR {many2one} IS NULL)
                AND (
                    {many2one} IN (
                        {subselect}
                        WHERE "res_partner"."function" LIKE %s
                    )
                    OR ({many2one} NOT IN (
                        {subselect}
                        WHERE "res_partner"."phone" LIKE %s
                    ) OR {many2one} IS NULL)
                )
            )
            ORDER BY "test_orm_multi"."id"
        """.format(
            many2one='"test_orm_multi"."partner"',
            subselect='SELECT "res_partner"."id" FROM "res_partner"',
        )]):
            # (function or not (phone)) and not website and (name or email)
            self.env['test_orm.multi'].search([
                '&', '&',
                    '|',
                        ('partner.function', 'like', 'Colonel'),
                        '!', ('partner.phone', 'like', '+01'),
                    '!', ('partner.website', 'like', 'sgc.us'),
                    '|',
                        ('partner.name', 'like', 'jack'),
                        ('partner.email', 'like', '@sgc.us'),
            ])

    def test_and_one2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE (EXISTS (SELECT FROM(
                SELECT "test_orm_multi_line"."multi" AS __inverse
                FROM "test_orm_multi_line"
                WHERE (
                    "test_orm_multi_line"."multi" IS NOT NULL
                    AND "test_orm_multi_line"."name" LIKE %s
                )
            ) AS __sub WHERE __inverse = "test_orm_multi"."id")
            AND EXISTS (SELECT FROM(
                SELECT "test_orm_multi_line"."multi" AS __inverse
                FROM "test_orm_multi_line"
                WHERE (
                    "test_orm_multi_line"."multi" IS NOT NULL
                    AND "test_orm_multi_line"."name" LIKE %s
                )
            ) AS __sub WHERE __inverse = "test_orm_multi"."id")
            )
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                ('lines.name', 'like', 'x'),
                ('lines.name', 'like', 'y'),
            ])

    def test_or_one2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE EXISTS (SELECT FROM(
                SELECT "test_orm_multi_line"."multi" AS __inverse
                FROM "test_orm_multi_line"
                WHERE (
                    "test_orm_multi_line"."multi" IS NOT NULL
                    AND (
                        "test_orm_multi_line"."name" LIKE %s
                        OR "test_orm_multi_line"."name" LIKE %s
                    )
                )
            ) AS __sub WHERE __inverse = "test_orm_multi"."id")
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                '|',
                    ('lines.name', 'like', 'x'),
                    ('lines.name', 'like', 'y'),
            ])

    def test_mixed_and_or_one2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE (EXISTS (SELECT FROM(
                SELECT "test_orm_multi_line"."multi" AS __inverse
                FROM "test_orm_multi_line"
                WHERE (
                    "test_orm_multi_line"."multi" IS NOT NULL
                    AND "test_orm_multi_line"."name" LIKE %s
                )
            ) AS __sub WHERE __inverse = "test_orm_multi"."id")
            AND EXISTS (SELECT FROM(
                SELECT "test_orm_multi_line"."multi" AS __inverse
                FROM "test_orm_multi_line"
                WHERE (
                    "test_orm_multi_line"."multi" IS NOT NULL
                    AND (
                        "test_orm_multi_line"."name" LIKE %s
                        OR "test_orm_multi_line"."name" LIKE %s
                    )
                )
            ) AS __sub WHERE __inverse = "test_orm_multi"."id")
            )
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                ('lines.name', 'like', 'x'),
                '|',
                    ('lines.name', 'like', 'y'),
                    ('lines.name', 'like', 'z'),
            ])

    def test_and_many2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE (EXISTS (
                SELECT 1
                FROM "test_orm_multi_test_orm_multi_tag_rel" AS "test_orm_multi__tags"
                WHERE "test_orm_multi__tags"."test_orm_multi_id" = "test_orm_multi"."id"
                AND "test_orm_multi__tags"."test_orm_multi_tag_id" IN (
                    SELECT "test_orm_multi_tag"."id"
                    FROM "test_orm_multi_tag"
                    WHERE (
                        "test_orm_multi_tag"."name" ILIKE %s
                        AND "test_orm_multi_tag"."name" LIKE %s
                    )
                )
            ) AND EXISTS (
                SELECT 1
                FROM "test_orm_multi_test_orm_multi_tag_rel" AS "test_orm_multi__tags"
                WHERE "test_orm_multi__tags"."test_orm_multi_id" = "test_orm_multi"."id"
                AND "test_orm_multi__tags"."test_orm_multi_tag_id" IN (
                    SELECT "test_orm_multi_tag"."id"
                    FROM "test_orm_multi_tag"
                    WHERE (
                        "test_orm_multi_tag"."name" ILIKE %s
                        AND "test_orm_multi_tag"."name" LIKE %s
                    )
                )
            ))
            ORDER BY "test_orm_multi"."id"
        """]):
            # each sub-query generates 2 comparisons with name:
            # one for 'a' (field context) and one from the domain
            self.env['test_orm.multi'].search([
                ('tags.name', 'like', 'x'),
                ('tags.name', 'like', 'y'),
            ])

    def test_or_many2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE EXISTS (
                SELECT 1
                FROM "test_orm_multi_test_orm_multi_tag_rel" AS "test_orm_multi__tags"
                WHERE "test_orm_multi__tags"."test_orm_multi_id" = "test_orm_multi"."id"
                AND "test_orm_multi__tags"."test_orm_multi_tag_id" IN (
                    SELECT "test_orm_multi_tag"."id"
                    FROM "test_orm_multi_tag"
                    WHERE (
                        "test_orm_multi_tag"."name" ILIKE %s
                        AND (
                            "test_orm_multi_tag"."name" LIKE %s
                            OR "test_orm_multi_tag"."name" LIKE %s
                        )
                    )
                )
            )
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                '|',
                    ('tags.name', 'like', 'x'),
                    ('tags.name', 'like', 'y'),
            ])

    def test_mixed_and_or_many2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE (
                EXISTS (
                    SELECT 1
                    FROM "test_orm_multi_test_orm_multi_tag_rel" AS "test_orm_multi__tags"
                    WHERE "test_orm_multi__tags"."test_orm_multi_id" = "test_orm_multi"."id"
                    AND "test_orm_multi__tags"."test_orm_multi_tag_id" IN (
                        SELECT "test_orm_multi_tag"."id"
                        FROM "test_orm_multi_tag"
                        WHERE (
                            "test_orm_multi_tag"."name" ILIKE %s
                            AND "test_orm_multi_tag"."name" LIKE %s
                        )
                    )
                ) AND EXISTS (
                    SELECT 1
                    FROM "test_orm_multi_test_orm_multi_tag_rel" AS "test_orm_multi__tags"
                    WHERE "test_orm_multi__tags"."test_orm_multi_id" = "test_orm_multi"."id"
                    AND "test_orm_multi__tags"."test_orm_multi_tag_id" IN (
                        SELECT "test_orm_multi_tag"."id"
                        FROM "test_orm_multi_tag"
                        WHERE (
                            "test_orm_multi_tag"."name" ILIKE %s
                            AND (
                                "test_orm_multi_tag"."name" LIKE %s
                                OR "test_orm_multi_tag"."name" LIKE %s
                            )
                        )
                    )
                )
            )
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([
                ('tags.name', 'like', 'x'),
                '|',
                    ('tags.name', 'like', 'y'),
                    ('tags.name', 'like', 'z'),
            ])

    def test_empty_many2many(self):
        sub_query = self.env['test_orm.multi'].tags._as_query()
        with self.assertQueries(["""
            SELECT "test_orm_multi"."id"
            FROM "test_orm_multi"
            WHERE FALSE
            ORDER BY "test_orm_multi"."id"
        """]):
            self.env['test_orm.multi'].search([('tags', 'any', sub_query)])

    def test_hierarchy(self):
        Head = self.env['test_orm.hierarchy.head']
        Node = self.env['test_orm.hierarchy.node']

        parent_node = Node.create({})
        nodes = Node.create([{'parent_id': parent_node.id} for _ in range(3)])
        Head.create({'node_id': parent_node.id})

        with self.assertQueries(["""
            SELECT "test_orm_hierarchy_node"."id"
            FROM "test_orm_hierarchy_node"
            WHERE "test_orm_hierarchy_node"."parent_id" IN %s
        """, """
            SELECT "test_orm_hierarchy_node"."id"
            FROM "test_orm_hierarchy_node"
            WHERE "test_orm_hierarchy_node"."parent_id" IN %s
        """, """
            SELECT "test_orm_hierarchy_head"."id"
            FROM "test_orm_hierarchy_head"
            WHERE "test_orm_hierarchy_head"."node_id" IN %s
            ORDER BY "test_orm_hierarchy_head"."id"
        """]):
            # 2 queries to resolve the hierarchy, 1 for the search
            Head.search([('node_id', 'child_of', parent_node.ids)])

        with self.assertQueries(["""
            SELECT "test_orm_hierarchy_head"."id"
            FROM "test_orm_hierarchy_head"
            WHERE "test_orm_hierarchy_head"."node_id" IN %s
            ORDER BY "test_orm_hierarchy_head"."id"
        """]):
            Head.search([('node_id', 'parent_of', nodes.ids)])


class TestSearchRelated(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.rule'].create([{
            'name': 'related',
            'model_id': cls.env['ir.model']._get('test_orm.related').id,
            'domain_force': "[('id', '<', 1000)]",
        }, {
            'name': 'related_foo',
            'model_id': cls.env['ir.model']._get('test_orm.related_foo').id,
            'domain_force': "[('id', '<', 1000)]",
        }, {
            'name': 'related_bar',
            'model_id': cls.env['ir.model']._get('test_orm.related_bar').id,
            'domain_force': "[('id', '<', 1000)]",
        }])

    def test_related_simple(self):
        model = self.env['test_orm.related'].with_user(self.env.ref('base.user_admin'))
        self.env['ir.rule'].create({
            'name': 'related_foo',
            'model_id': self.env['ir.model']._get('test_orm.related_foo').id,
            'domain_force': "[('id', '<', 1000)]",
        })

        # warmup
        model.search([('foo_name', '=', 'a')])
        model.search([('foo_name_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE ("test_orm_related"."foo_id" IS NOT NULL AND "test_orm_related__foo_id"."name" IN %s)
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."name" IN %s
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name', '=', 'a')])

    def test_related_many2one(self):
        model = self.env['test_orm.related'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search([('foo_bar_id', '=', 42)])
        model.search([('foo_bar_id.name', '=', 'a')])
        model.search([('foo_bar_sudo_id', '=', 42)])
        model.search([('foo_bar_sudo_id.name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."bar_id" IN %s
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_id', '=', 42)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE "test_orm_related_bar"."name" IN %s
                    AND "test_orm_related_bar"."id" < %s
                )
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_id.name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE (
                "test_orm_related"."foo_id" IS NOT NULL
                AND "test_orm_related__foo_id"."bar_id" IN %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_sudo_id', '=', 42)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE ("test_orm_related"."foo_id" IS NOT NULL
                AND "test_orm_related__foo_id"."bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE "test_orm_related_bar"."name" IN %s
                    AND "test_orm_related_bar"."id" < %s
                )
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_sudo_id.name', '=', 'a')])

    def test_related_many2many(self):
        model = self.env['test_orm.related'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search([('foo_bar_ids', '=', 42)])
        model.search([('foo_bar_ids.name', '=', 'a')])
        model.search([('foo_bar_sudo_ids', '=', 42)])
        model.search([('foo_bar_sudo_ids.name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE EXISTS (
                    SELECT 1
                    FROM "test_orm_related_bar_test_orm_related_foo_rel" AS "test_orm_related_foo__bar_ids"
                    WHERE "test_orm_related_foo__bar_ids"."test_orm_related_foo_id" = "test_orm_related_foo"."id"
                    AND "test_orm_related_foo__bar_ids"."test_orm_related_bar_id" IN %s
                )
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_ids', '=', 42)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE EXISTS (
                    SELECT 1
                    FROM "test_orm_related_bar_test_orm_related_foo_rel" AS "test_orm_related_foo__bar_ids"
                    WHERE "test_orm_related_foo__bar_ids"."test_orm_related_foo_id" = "test_orm_related_foo"."id"
                    AND "test_orm_related_foo__bar_ids"."test_orm_related_bar_id" IN (
                        SELECT "test_orm_related_bar"."id"
                        FROM "test_orm_related_bar"
                        WHERE ("test_orm_related_bar"."active" IS TRUE AND "test_orm_related_bar"."name" IN %s)
                        AND "test_orm_related_bar"."id" < %s
                    )
                )
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_ids.name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE ("test_orm_related"."foo_id" IS NOT NULL AND EXISTS (
                SELECT 1
                FROM "test_orm_related_bar_test_orm_related_foo_rel" AS "test_orm_related__foo_id__bar_ids"
                WHERE "test_orm_related__foo_id__bar_ids"."test_orm_related_foo_id" = "test_orm_related__foo_id"."id"
                AND "test_orm_related__foo_id__bar_ids"."test_orm_related_bar_id" IN %s
            ))
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_sudo_ids', '=', 42)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE ("test_orm_related"."foo_id" IS NOT NULL AND EXISTS (
                SELECT 1
                FROM "test_orm_related_bar_test_orm_related_foo_rel" AS "test_orm_related__foo_id__bar_ids"
                WHERE "test_orm_related__foo_id__bar_ids"."test_orm_related_foo_id" = "test_orm_related__foo_id"."id"
                AND "test_orm_related__foo_id__bar_ids"."test_orm_related_bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE ("test_orm_related_bar"."active" IS TRUE AND "test_orm_related_bar"."name" IN %s)
                    AND "test_orm_related_bar"."id" < %s
                )
            ))
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_sudo_ids.name', '=', 'a')])

    def test_related_one2many(self):
        model = self.env['test_orm.related'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search([('foo_foo_ids', '=', 42)])
        model.search([('foo_foo_ids.name', '=', 'a')])
        model.search([('foo_foo_sudo_ids', '=', 42)])
        model.search([('foo_foo_sudo_ids.name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE EXISTS(SELECT FROM (
                    SELECT "test_orm_related"."foo_id" AS __inverse
                    FROM "test_orm_related"
                    WHERE "test_orm_related"."id" IN %s
                    AND "test_orm_related"."foo_id" IS NOT NULL
                ) AS __sub WHERE __inverse = "test_orm_related_foo"."id")
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_foo_ids', '=', 42)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE EXISTS(SELECT FROM (
                    SELECT "test_orm_related"."foo_id" AS __inverse
                    FROM "test_orm_related"
                    WHERE ("test_orm_related"."foo_id" IS NOT NULL AND "test_orm_related"."name" IN %s)
                    AND "test_orm_related"."id" < %s
                ) AS __sub WHERE __inverse = "test_orm_related_foo"."id")
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_foo_ids.name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE ("test_orm_related"."foo_id" IS NOT NULL
                AND EXISTS(SELECT FROM (
                    SELECT "test_orm_related"."foo_id" AS __inverse
                    FROM "test_orm_related"
                    WHERE "test_orm_related"."id" IN %s
                    AND "test_orm_related"."foo_id" IS NOT NULL
                ) AS __sub WHERE __inverse = "test_orm_related__foo_id"."id")
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_foo_sudo_ids', '=', 42)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE ("test_orm_related"."foo_id" IS NOT NULL
                AND EXISTS(SELECT FROM (
                    SELECT "test_orm_related"."foo_id" AS __inverse
                    FROM "test_orm_related"
                    WHERE (
                        "test_orm_related"."foo_id" IS NOT NULL
                        AND "test_orm_related"."name" IN %s
                    )
                    AND "test_orm_related"."id" < %s
                ) AS __sub WHERE __inverse = "test_orm_related__foo_id"."id")
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_foo_sudo_ids.name', '=', 'a')])

    def test_related_binary(self):
        model = self.env['test_orm.related'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search([('foo_binary_att', '!=', False)])
        model.search([('foo_binary_bin', '!=', False)])
        model.search([('foo_binary_att_sudo', '!=', False)])
        model.search([('foo_binary_bin_sudo', '!=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."id" IN (
                    SELECT res_id FROM ir_attachment WHERE res_model = %s AND res_field = %s
                )
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_binary_att', '!=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."binary_bin" IS NOT NULL
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_binary_bin', '!=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE (
                "test_orm_related"."foo_id" IS NOT NULL
                AND "test_orm_related__foo_id"."id" IN (
                    SELECT res_id FROM ir_attachment WHERE res_model = %s AND res_field = %s
                )
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_binary_att_sudo', '!=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE (
                "test_orm_related"."foo_id" IS NOT NULL
                AND "test_orm_related__foo_id"."binary_bin" IS NOT NULL
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_binary_bin_sudo', '!=', False)])

    def test_related_multi(self):
        model = self.env['test_orm.related'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search([('foo_bar_name', '=', 'a')])
        model.search([('foo_bar_name_sudo', '=', 'a')])
        model.search([('foo_id_bar_name', '=', 'a')])
        model.search([('foo_bar_id_name', '=', 'a')])
        model.search([('foo_bar_sudo_id_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            LEFT JOIN "test_orm_related_bar" AS "test_orm_related__foo_id__bar_id"
                ON ("test_orm_related__foo_id"."bar_id" = "test_orm_related__foo_id__bar_id"."id")
            WHERE ("test_orm_related"."foo_id" IS NOT NULL AND (
                "test_orm_related__foo_id"."bar_id" IS NOT NULL
                AND "test_orm_related__foo_id__bar_id"."name" IN %s
            ))
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_name_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE "test_orm_related_bar"."name" IN %s
                    AND "test_orm_related_bar"."id" < %s
                )
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE "test_orm_related_bar"."name" IN %s
                    AND "test_orm_related_bar"."id" < %s
                )
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_id_bar_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE "test_orm_related_bar"."name" IN %s
                    AND "test_orm_related_bar"."id" < %s
                )
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_id_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE (
                "test_orm_related"."foo_id" IS NOT NULL
                AND "test_orm_related__foo_id"."bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE "test_orm_related_bar"."name" IN %s
                    AND "test_orm_related_bar"."id" < %s
                )
            )
            AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_sudo_id_name', '=', 'a')])

    def test_related_through_one2many(self):
        model = self.env['test_orm.related_foo'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search([('foo_names', '=', 'a')])
        model.search([('foo_names_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related_foo"."id"
            FROM "test_orm_related_foo"
            WHERE EXISTS (SELECT FROM(
                SELECT "test_orm_related"."foo_id" AS __inverse
                FROM "test_orm_related"
                WHERE (
                    "test_orm_related"."foo_id" IS NOT NULL
                    AND "test_orm_related"."name" IN %s
                ) AND "test_orm_related"."id" < %s
            ) AS __sub WHERE __inverse = "test_orm_related_foo"."id"
            ) AND "test_orm_related_foo"."id" < %s
            ORDER BY "test_orm_related_foo"."id"
        """]):
            model.search([('foo_names', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related_foo"."id"
            FROM "test_orm_related_foo"
            WHERE EXISTS (SELECT FROM(
                SELECT "test_orm_related"."foo_id" AS __inverse
                FROM "test_orm_related"
                WHERE (
                    "test_orm_related"."foo_id" IS NOT NULL
                    AND "test_orm_related"."name" IN %s
                )
            ) AS __sub WHERE __inverse = "test_orm_related_foo"."id"
            ) AND "test_orm_related_foo"."id" < %s
            ORDER BY "test_orm_related_foo"."id"
        """]):
            model.search([('foo_names_sudo', '=', 'a')])

    def test_related_through_many2many(self):
        model = self.env['test_orm.related_foo'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search([('bar_names', '=', 'a')])
        model.search([('bar_names_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related_foo"."id"
            FROM "test_orm_related_foo"
            WHERE EXISTS (
                SELECT 1
                FROM "test_orm_related_bar_test_orm_related_foo_rel" AS "test_orm_related_foo__bar_ids"
                WHERE "test_orm_related_foo__bar_ids"."test_orm_related_foo_id" = "test_orm_related_foo"."id"
                AND "test_orm_related_foo__bar_ids"."test_orm_related_bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE ("test_orm_related_bar"."active" IS TRUE AND "test_orm_related_bar"."name" IN %s)
                    AND "test_orm_related_bar"."id" < %s
                )
            ) AND "test_orm_related_foo"."id" < %s
            ORDER BY "test_orm_related_foo"."id"
        """]):
            model.search([('bar_names', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related_foo"."id"
            FROM "test_orm_related_foo"
            WHERE EXISTS (
                SELECT 1
                FROM "test_orm_related_bar_test_orm_related_foo_rel" AS "test_orm_related_foo__bar_ids"
                WHERE "test_orm_related_foo__bar_ids"."test_orm_related_foo_id" = "test_orm_related_foo"."id"
                AND "test_orm_related_foo__bar_ids"."test_orm_related_bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE ("test_orm_related_bar"."active" IS TRUE AND "test_orm_related_bar"."name" IN %s)
                )
            ) AND "test_orm_related_foo"."id" < %s
            ORDER BY "test_orm_related_foo"."id"
        """]):
            model.search([('bar_names_sudo', '=', 'a')])

    def test_related_null(self):
        model = self.env['test_orm.related']

        # warmup
        model.search([('foo_name', '=', 'a')])
        model.search([('foo_name', '!=', 'a')])
        model.search([('foo_name', '=', False)])
        model.search([('foo_name', '!=', False)])
        model.search([('foo_name', 'in', ['a', 'b'])])
        model.search([('foo_name', 'not in', ['a', 'b'])])
        model.search([('foo_name', 'in', ['a', False])])
        model.search([('foo_name', 'not in', ['a', False])])
        model.search([('foo_name_sudo', '!=', 'a')])
        model.search([('foo_name_sudo', '=', False)])
        model.search([('foo_bar_name', '=', False)])
        model.search([('foo_bar_name', '!=', False)])
        model.search([('foo_bar_name_sudo', '=', False)])
        model.search([('foo_bar_name_sudo', '!=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."name" IN %s
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE (
                "test_orm_related"."foo_id" NOT IN (
                    SELECT "test_orm_related_foo"."id"
                    FROM "test_orm_related_foo"
                    WHERE "test_orm_related_foo"."name" IN %s
                ) OR "test_orm_related"."foo_id" IS NULL
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name', '!=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE (
                "test_orm_related"."foo_id" IS NULL
                OR "test_orm_related"."foo_id" IN (
                    SELECT "test_orm_related_foo"."id"
                    FROM "test_orm_related_foo"
                    WHERE ("test_orm_related_foo"."name" IN %s OR "test_orm_related_foo"."name" IS NULL)
                )
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name', '=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."name" NOT IN %s
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name', '!=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."name" IN %s
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name', 'in', ['a', 'b'])])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE (
                "test_orm_related"."foo_id" NOT IN (
                    SELECT "test_orm_related_foo"."id"
                    FROM "test_orm_related_foo"
                    WHERE "test_orm_related_foo"."name" IN %s
                ) OR "test_orm_related"."foo_id" IS NULL
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name', 'not in', ['a', 'b'])])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE (
                "test_orm_related"."foo_id" IS NULL
                OR "test_orm_related"."foo_id" IN (
                    SELECT "test_orm_related_foo"."id"
                    FROM "test_orm_related_foo"
                    WHERE (
                        "test_orm_related_foo"."name" IN %s
                        OR "test_orm_related_foo"."name" IS NULL
                    )
                )
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name', 'in', ['a', False])])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."name" NOT IN %s
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name', 'not in', ['a', False])])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE (
                "test_orm_related"."foo_id" IS NULL
                OR ("test_orm_related__foo_id"."name" IN %s) IS NOT TRUE
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name_sudo', '!=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE ("test_orm_related"."foo_id" IS NULL OR (
                "test_orm_related"."foo_id" IS NOT NULL AND (
                    "test_orm_related__foo_id"."name" IN %s
                    OR "test_orm_related__foo_id"."name" IS NULL
                )
            ))
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_name_sudo', '=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE (
                "test_orm_related"."foo_id" IS NULL
                OR "test_orm_related"."foo_id" IN (
                    SELECT "test_orm_related_foo"."id"
                    FROM "test_orm_related_foo"
                    WHERE (
                        "test_orm_related_foo"."bar_id" IS NULL
                        OR "test_orm_related_foo"."bar_id" IN (
                            SELECT "test_orm_related_bar"."id"
                            FROM "test_orm_related_bar"
                            WHERE ("test_orm_related_bar"."name" IN %s OR "test_orm_related_bar"."name" IS NULL)
                        )
                    )
                )
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_name', '=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE "test_orm_related_bar"."name" NOT IN %s
                )
            )
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_name', '!=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            LEFT JOIN "test_orm_related_bar" AS "test_orm_related__foo_id__bar_id"
                ON ("test_orm_related__foo_id"."bar_id" = "test_orm_related__foo_id__bar_id"."id")
            WHERE ("test_orm_related"."foo_id" IS NULL OR (
                "test_orm_related"."foo_id" IS NOT NULL AND (
                    "test_orm_related__foo_id"."bar_id" IS NULL
                    OR ("test_orm_related__foo_id"."bar_id" IS NOT NULL AND (
                        "test_orm_related__foo_id__bar_id"."name" IN %s
                        OR "test_orm_related__foo_id__bar_id"."name" IS NULL
                    ))
                )
            ))
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_name_sudo', '=', False)])

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            LEFT JOIN "test_orm_related_bar" AS "test_orm_related__foo_id__bar_id"
                ON ("test_orm_related__foo_id"."bar_id" = "test_orm_related__foo_id__bar_id"."id")
            WHERE ("test_orm_related"."foo_id" IS NOT NULL AND (
                "test_orm_related__foo_id"."bar_id" IS NOT NULL
                AND "test_orm_related__foo_id__bar_id"."name" NOT IN %s
            ))
            ORDER BY "test_orm_related"."id"
        """]):
            model.search([('foo_bar_name_sudo', '!=', False)])

    def test_related_inherited(self):
        model = self.env['test_orm.related_inherits'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search([('name', '=', 'a')])
        model.search([('foo_name', '=', 'a')])
        model.search([('foo_name_sudo', '=', 'a')])
        model.search([('foo_bar_name', '=', 'a')])
        model.search([('foo_bar_name_sudo', '=', 'a')])

        # search on inherited fields
        with self.assertQueries(["""
            SELECT "test_orm_related_inherits"."id"
            FROM "test_orm_related_inherits"
            LEFT JOIN "test_orm_related" AS "test_orm_related_inherits__base_id"
                ON ("test_orm_related_inherits"."base_id" = "test_orm_related_inherits__base_id"."id")
            WHERE "test_orm_related_inherits__base_id"."name" IN %s
            AND "test_orm_related_inherits__base_id"."id" < %s
            ORDER BY "test_orm_related_inherits"."id"
        """]):
            model.search([('name', '=', 'a')])

        # search on inherited related fields
        with self.assertQueries(["""
            SELECT "test_orm_related_inherits"."id"
            FROM "test_orm_related_inherits"
            LEFT JOIN "test_orm_related" AS "test_orm_related_inherits__base_id"
                ON ("test_orm_related_inherits"."base_id" = "test_orm_related_inherits__base_id"."id")
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related_inherits__base_id__foo_id"
                ON ("test_orm_related_inherits__base_id"."foo_id" = "test_orm_related_inherits__base_id__foo_id"."id")
            WHERE (
                "test_orm_related_inherits__base_id"."foo_id" IS NOT NULL
                AND "test_orm_related_inherits__base_id__foo_id"."name" IN %s
            )
            AND "test_orm_related_inherits__base_id"."id" < %s
            ORDER BY "test_orm_related_inherits"."id"
        """]):
            model.search([('foo_name_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related_inherits"."id"
            FROM "test_orm_related_inherits"
            LEFT JOIN "test_orm_related" AS "test_orm_related_inherits__base_id"
                ON ("test_orm_related_inherits"."base_id" = "test_orm_related_inherits__base_id"."id")
            WHERE "test_orm_related_inherits__base_id"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."name" IN %s
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related_inherits__base_id"."id" < %s
            ORDER BY "test_orm_related_inherits"."id"
        """]):
            model.search([('foo_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related_inherits"."id"
            FROM "test_orm_related_inherits"
            LEFT JOIN "test_orm_related" AS "test_orm_related_inherits__base_id"
                ON ("test_orm_related_inherits"."base_id" = "test_orm_related_inherits__base_id"."id")
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related_inherits__base_id__foo_id"
                ON ("test_orm_related_inherits__base_id"."foo_id" = "test_orm_related_inherits__base_id__foo_id"."id")
            LEFT JOIN "test_orm_related_bar" AS "test_orm_related_inherits__base_id__foo_id__bar_id"
                ON ("test_orm_related_inherits__base_id__foo_id"."bar_id" = "test_orm_related_inherits__base_id__foo_id__bar_id"."id")
            WHERE (
                "test_orm_related_inherits__base_id"."foo_id" IS NOT NULL AND (
                    "test_orm_related_inherits__base_id__foo_id"."bar_id" IS NOT NULL
                    AND "test_orm_related_inherits__base_id__foo_id__bar_id"."name" IN %s
                )
            )
            AND "test_orm_related_inherits__base_id"."id" < %s
            ORDER BY "test_orm_related_inherits"."id"
        """]):
            model.search([('foo_bar_name_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_orm_related_inherits"."id"
            FROM "test_orm_related_inherits"
            LEFT JOIN "test_orm_related" AS "test_orm_related_inherits__base_id"
                ON ("test_orm_related_inherits"."base_id" = "test_orm_related_inherits__base_id"."id")
            WHERE "test_orm_related_inherits__base_id"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE "test_orm_related_bar"."name" IN %s
                    AND "test_orm_related_bar"."id" < %s
                )
                AND "test_orm_related_foo"."id" < %s
            )
            AND "test_orm_related_inherits__base_id"."id" < %s
            ORDER BY "test_orm_related_inherits"."id"
        """]):
            model.search([('foo_bar_name', '=', 'a')])


class TestSearchAny(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.rule'].create([{
            'name': 'related',
            'model_id': cls.env['ir.model']._get('test_orm.related').id,
            'domain_force': "[('id', '<', 1000)]",
        }, {
            'name': 'related_foo',
            'model_id': cls.env['ir.model']._get('test_orm.related_foo').id,
            'domain_force': "[('id', '<', 1000)]",
        }, {
            'name': 'related_bar',
            'model_id': cls.env['ir.model']._get('test_orm.related_bar').id,
            'domain_force': "[('id', '<', 1000)]",
        }])

    def test_many2one_any(self):
        model = self.env['test_orm.related'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search(Domain('foo_id', 'any', Domain('bar_id', 'any', Domain('name', '=', 'a'))))
        model.search(Domain('foo_id', 'any!', Domain('bar_id', 'any', Domain('name', '=', 'a'))))

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."name" IN %s
                AND "test_orm_related_foo"."id" < %s
            ) AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search(Domain('foo_id', 'any', Domain('name', '=', 'a')))

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE "test_orm_related"."foo_id" IN (
                SELECT "test_orm_related_foo"."id"
                FROM "test_orm_related_foo"
                WHERE "test_orm_related_foo"."bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE "test_orm_related_bar"."name" IN %s
                    AND "test_orm_related_bar"."id" < %s
                ) AND "test_orm_related_foo"."id" < %s
            ) AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search(Domain('foo_id', 'any', Domain('bar_id', 'any', Domain('name', '=', 'a'))))

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE (
                "test_orm_related"."foo_id" IS NOT NULL
                AND "test_orm_related__foo_id"."name" IN %s
            ) AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search(Domain('foo_id', 'any!', Domain('name', '=', 'a')))

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            LEFT JOIN "test_orm_related_foo" AS "test_orm_related__foo_id"
                ON ("test_orm_related"."foo_id" = "test_orm_related__foo_id"."id")
            WHERE (
                "test_orm_related"."foo_id" IS NOT NULL
                AND "test_orm_related__foo_id"."bar_id" IN (
                    SELECT "test_orm_related_bar"."id"
                    FROM "test_orm_related_bar"
                    WHERE "test_orm_related_bar"."name" IN %s
                    AND "test_orm_related_bar"."id" < %s
                )
            ) AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search(Domain('foo_id', 'any!', Domain('bar_id', 'any', Domain('name', '=', 'a'))))

    def test_one2many_any(self):
        model = self.env['test_orm.related_foo'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search(Domain('foo_ids', 'any', Domain('foo_id', 'any', Domain('name', '=', 'a'))))

        with self.assertQueries(["""
            SELECT "test_orm_related_foo"."id"
            FROM "test_orm_related_foo"
            WHERE EXISTS (SELECT FROM (
                SELECT "test_orm_related"."foo_id" AS __inverse
                FROM "test_orm_related"
                WHERE (
                    "test_orm_related"."foo_id" IS NOT NULL
                    AND "test_orm_related"."name" IN %s
                ) AND "test_orm_related"."id" < %s
            ) AS __sub WHERE __inverse = "test_orm_related_foo"."id"
            ) AND "test_orm_related_foo"."id" < %s
            ORDER BY "test_orm_related_foo"."id"
        """]):
            model.search(Domain('foo_ids', 'any', Domain('name', '=', 'a')))

        with self.assertQueries(["""
            SELECT "test_orm_related_foo"."id"
            FROM "test_orm_related_foo"
            WHERE EXISTS (SELECT FROM (
                SELECT "test_orm_related"."foo_id" AS __inverse
                FROM "test_orm_related"
                WHERE (
                    "test_orm_related"."foo_id" IS NOT NULL
                    AND "test_orm_related"."foo_id" IN (
                        SELECT "test_orm_related_foo"."id"
                        FROM "test_orm_related_foo"
                        WHERE "test_orm_related_foo"."name" IN %s
                        AND "test_orm_related_foo"."id" < %s
                    )
                ) AND "test_orm_related"."id" < %s
            ) AS __sub WHERE __inverse = "test_orm_related_foo"."id"
            ) AND "test_orm_related_foo"."id" < %s
            ORDER BY "test_orm_related_foo"."id"
        """]):
            model.search(Domain('foo_ids', 'any', Domain('foo_id', 'any', Domain('name', '=', 'a'))))

        with self.assertQueries(["""
            SELECT "test_orm_related_foo"."id"
            FROM "test_orm_related_foo"
            WHERE EXISTS (SELECT FROM (
                SELECT "test_orm_related"."foo_id" AS __inverse
                FROM "test_orm_related"
                WHERE (
                    "test_orm_related"."foo_id" IS NOT NULL
                    AND "test_orm_related"."name" IN %s
                )
            ) AS __sub WHERE __inverse = "test_orm_related_foo"."id"
            ) AND "test_orm_related_foo"."id" < %s
            ORDER BY "test_orm_related_foo"."id"
        """]):
            model.search(Domain('foo_ids', 'any!', Domain('name', '=', 'a')))

        with self.assertQueries(["""
            SELECT "test_orm_related_foo"."id"
            FROM "test_orm_related_foo"
            WHERE EXISTS (SELECT FROM (
                SELECT "test_orm_related"."foo_id" AS __inverse
                FROM "test_orm_related"
                WHERE (
                    "test_orm_related"."foo_id" IS NOT NULL
                    AND "test_orm_related"."foo_id" IN (
                        SELECT "test_orm_related_foo"."id"
                        FROM "test_orm_related_foo"
                        WHERE "test_orm_related_foo"."name" IN %s
                        AND "test_orm_related_foo"."id" < %s
                    )
                )
            ) AS __sub WHERE __inverse = "test_orm_related_foo"."id"
            ) AND "test_orm_related_foo"."id" < %s
            ORDER BY "test_orm_related_foo"."id"
        """]):
            model.search(Domain('foo_ids', 'any!', Domain('foo_id', 'any', Domain('name', '=', 'a'))))

    def test_many2many_any(self):
        model = self.env['test_orm.related'].with_user(self.env.ref('base.user_admin'))

        # warmup
        model.search(Domain('foo_ids', 'any', Domain('bar_id', 'any', Domain('name', '=', 'a'))))

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE EXISTS (
                SELECT 1
                FROM "test_orm_related_test_orm_related_foo_rel" AS "test_orm_related__foo_ids"
                WHERE "test_orm_related__foo_ids"."test_orm_related_id" = "test_orm_related"."id"
                AND "test_orm_related__foo_ids"."test_orm_related_foo_id" IN (
                    SELECT "test_orm_related_foo"."id"
                    FROM "test_orm_related_foo"
                    WHERE "test_orm_related_foo"."name" IN %s
                    AND "test_orm_related_foo"."id" < %s
                )
            ) AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search(Domain('foo_ids', 'any', Domain('name', '=', 'a')))

        with self.assertQueries(["""
            SELECT "test_orm_related"."id"
            FROM "test_orm_related"
            WHERE EXISTS (
                SELECT 1
                FROM "test_orm_related_test_orm_related_foo_rel" AS "test_orm_related__foo_ids"
                WHERE "test_orm_related__foo_ids"."test_orm_related_id" = "test_orm_related"."id"
                AND "test_orm_related__foo_ids"."test_orm_related_foo_id" IN (
                    SELECT "test_orm_related_foo"."id"
                    FROM "test_orm_related_foo"
                    WHERE "test_orm_related_foo"."bar_id" IN (
                        SELECT "test_orm_related_bar"."id"
                        FROM "test_orm_related_bar"
                        WHERE "test_orm_related_bar"."name" IN %s
                        AND "test_orm_related_bar"."id" < %s
                    ) AND "test_orm_related_foo"."id" < %s
                )
            ) AND "test_orm_related"."id" < %s
            ORDER BY "test_orm_related"."id"
        """]):
            model.search(Domain('foo_ids', 'any', Domain('bar_id', 'any', Domain('name', '=', 'a'))))


class TestFlushSearch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env['test_orm.city']
        cls.belgium, cls.france = cls.env['test_orm.country'].create([
            {'name': 'Belgium'}, {'name': 'France'},
        ])
        cls.brussels, cls.paris = cls.env['test_orm.city'].create([
            {'name': "Brussels", 'country_id': cls.belgium.id},
            {'name': "Paris", 'country_id': cls.france.id},
        ])

    def test_flush_fields_in_domain(self):
        with self.assertQueries(['''
            UPDATE "test_orm_city"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_orm_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_city"."id"
            FROM "test_orm_city"
            WHERE "test_orm_city"."name" LIKE %s
            ORDER BY "test_orm_city"."id"
        ''']):
            self.brussels.name = "Bruxelles"
            self.model.search([('name', 'like', 'foo')], order='id')

    def test_flush_fields_in_subdomain(self):
        with self.assertQueries(['''
            UPDATE "test_orm_city"
            SET "country_id" = "__tmp"."country_id"::int4,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "country_id", "write_date", "write_uid")
            WHERE "test_orm_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_city"."id"
            FROM "test_orm_city"
            WHERE "test_orm_city"."country_id" IN (
                SELECT "test_orm_country"."id"
                FROM "test_orm_country"
                WHERE "test_orm_country"."name" LIKE %s
            )
            ORDER BY "test_orm_city"."id"
        ''']):
            self.brussels.country_id = self.france
            self.model.search([('country_id.name', 'like', 'foo')], order='id')

        with self.assertQueries(['''
            UPDATE "test_orm_country"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_orm_country"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_city"."id"
            FROM "test_orm_city"
            WHERE "test_orm_city"."country_id" IN (
                SELECT "test_orm_country"."id"
                FROM "test_orm_country"
                WHERE "test_orm_country"."name" LIKE %s
            )
            ORDER BY "test_orm_city"."id"
        ''']):
            self.belgium.name = "Belgique"
            self.model.search([('country_id.name', 'like', 'foo')], order='id')

    def test_flush_bypass_access_field_in_domain(self):
        self.patch(self.env.registry['test_orm.city'].country_id, 'bypass_search_access', True)

        with self.assertQueries(['''
            UPDATE "test_orm_city"
            SET "country_id" = "__tmp"."country_id"::int4,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "country_id", "write_date", "write_uid")
            WHERE "test_orm_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_city"."id"
            FROM "test_orm_city"
            LEFT JOIN "test_orm_country" AS "test_orm_city__country_id"
                ON ("test_orm_city"."country_id" = "test_orm_city__country_id"."id")
            WHERE ("test_orm_city"."country_id" IS NOT NULL AND "test_orm_city__country_id"."name" LIKE %s)
            ORDER BY "test_orm_city"."id"
        ''']):
            self.brussels.country_id = self.france
            self.model.search([('country_id.name', 'like', 'foo')], order='id')

    def test_flush_inherited_field_in_domain(self):
        payment = self.env['test_orm.payment'].create({})
        move = self.env['test_orm.move'].create({})

        with self.assertQueries(['''
            UPDATE "test_orm_payment"
            SET "move_id" = "__tmp"."move_id"::int4,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "move_id", "write_date", "write_uid")
            WHERE "test_orm_payment"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_payment"."id"
            FROM "test_orm_payment"
            LEFT JOIN "test_orm_move" AS "test_orm_payment__move_id"
                ON ("test_orm_payment"."move_id" = "test_orm_payment__move_id"."id")
            WHERE "test_orm_payment__move_id"."tag_repeat" > %s
            ORDER BY "test_orm_payment"."id"
        ''']):
            payment.move_id = move
            payment.search([('tag_repeat', '>', 0)], order='id')

        with self.assertQueries(['''
            UPDATE "test_orm_move"
            SET "tag_repeat" = "__tmp"."tag_repeat"::int4,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "tag_repeat", "write_date", "write_uid")
            WHERE "test_orm_move"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_payment"."id"
            FROM "test_orm_payment"
            LEFT JOIN "test_orm_move" AS "test_orm_payment__move_id"
                ON ("test_orm_payment"."move_id" = "test_orm_payment__move_id"."id")
            WHERE "test_orm_payment__move_id"."tag_repeat" > %s
            ORDER BY "test_orm_payment"."id"
        ''']):
            payment.move_id.tag_repeat = 1
            payment.search([('tag_repeat', '>', 0)], order='id')

    def test_flush_fields_in_access_rules(self):
        model = self.model.with_user(self.env.ref('base.user_admin'))
        self.env['ir.rule'].create({
            'name': 'city_rule',
            'model_id': self.env['ir.model']._get(model._name).id,
            'domain_force': str([('name', 'like', 'a')]),
        })
        model.search([])

        with self.assertQueries(['''
            UPDATE "test_orm_city"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_orm_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_city"."id"
            FROM "test_orm_city"
            WHERE "test_orm_city"."id" IN %s AND "test_orm_city"."name" LIKE %s
            ORDER BY "test_orm_city"."id"
        ''']):
            self.brussels.name = "Bruxelles"
            model.search([('id', '=', self.paris.id)], order='id')

    def test_flush_fields_in_order(self):
        with self.assertQueries(['''
            UPDATE "test_orm_city"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_orm_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_city"."id"
            FROM "test_orm_city"
            WHERE "test_orm_city"."id" IN %s
            ORDER BY "test_orm_city"."name", "test_orm_city"."id"
        ''']):
            self.brussels.name = "Bruxelles"
            self.model.search([('id', '=', self.paris.id)], order='name, id')

        # test indirect fields, when ordering by many2one field
        with self.assertQueries(['''
            UPDATE "test_orm_country"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_orm_country"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_city"."id"
            FROM "test_orm_city"
            LEFT JOIN "test_orm_country" AS "test_orm_city__country_id"
                ON ("test_orm_city"."country_id" = "test_orm_city__country_id"."id")
            WHERE "test_orm_city"."id" IN %s
            ORDER BY "test_orm_city__country_id"."name",
                    "test_orm_city__country_id"."id",
                    "test_orm_city"."id"
        ''']):
            self.belgium.name = "Belgique"
            self.model.search([('id', '=', self.paris.id)], order='country_id, id')

        with self.assertQueries(['''
            UPDATE "test_orm_city"
            SET "country_id" = "__tmp"."country_id"::int4,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "country_id", "write_date", "write_uid")
            WHERE "test_orm_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_city"."id"
            FROM "test_orm_city"
            LEFT JOIN "test_orm_country" AS "test_orm_city__country_id"
                ON ("test_orm_city"."country_id" = "test_orm_city__country_id"."id")
            WHERE "test_orm_city"."id" IN %s
            ORDER BY "test_orm_city__country_id"."name",
                    "test_orm_city__country_id"."id",
                    "test_orm_city"."id"
        ''']):
            self.brussels.country_id = self.france
            self.model.search([('id', '=', self.paris.id)], order='country_id, id')

    def test_do_not_flush_fields_to_fetch(self):
        with self.assertQueries(['''
            SELECT "test_orm_city"."id", "test_orm_city"."name"
            FROM "test_orm_city"
            WHERE "test_orm_city"."id" IN %s
            ORDER BY "test_orm_city"."id"
        '''], flush=False):
            self.brussels.name = "Bruxelles"
            self.model.search_fetch([('id', '=', self.brussels.id)], ['name'], order='id')

        # except when the field appears in another clause
        with self.assertQueries(['''
            UPDATE "test_orm_city"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_orm_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_city"."id", "test_orm_city"."name"
            FROM "test_orm_city"
            WHERE "test_orm_city"."name" LIKE %s
            ORDER BY "test_orm_city"."id"
        '''], flush=False):
            self.brussels.name = "Brussel"
            self.model.search_fetch([('name', 'like', 'Brussel')], ['name'], order='id')

        with self.assertQueries(['''
            UPDATE "test_orm_city"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_orm_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_orm_city"."id", "test_orm_city"."name"
            FROM "test_orm_city"
            WHERE "test_orm_city"."id" IN %s
            ORDER BY "test_orm_city"."name"
        '''], flush=False):
            self.brussels.name = "Brüsel"
            self.model.search_fetch([('id', '=', self.brussels.id)], ['name'], order='name')

    def test_search_fetch_prefetchable(self):
        self.assertEqual(
            {field.name for field in self.model._fields.values() if field.prefetch is True},
            {'name', 'country_id', 'create_uid', 'create_date', 'write_uid', 'write_date'},
        )

        with self.assertQueries(['''
            SELECT "test_orm_city"."id", "test_orm_city"."name", "test_orm_city"."country_id",
                   "test_orm_city"."create_uid", "test_orm_city"."create_date",
                   "test_orm_city"."write_uid", "test_orm_city"."write_date"
            FROM "test_orm_city"
            WHERE "test_orm_city"."id" IN %s
            ORDER BY "test_orm_city"."id"
        ''']):
            self.model.search_fetch([('id', '=', self.brussels.id)], order='id')

    def test_depends_with_view_model(self):
        parent = self.env['test_orm.any.parent'].create({'name': 'parent'})
        child = self.env['test_orm.any.child'].create({
            'parent_id': parent.id,
            'quantity': 10,
            'tag_ids': [Command.create({'name': 'tag1'})],
        })

        self.assertEqual(self.env['test_orm.custom.view'].search([]).sum_quantity, 10)
        # _depends doesn't invalidate the cache of the model, should it ?
        self.env['test_orm.custom.view'].invalidate_model()
        child.quantity = 25
        self.assertEqual(self.env['test_orm.custom.view'].search([]).sum_quantity, 25)

    def test_depends_with_table_query_model(self):
        parent = self.env['test_orm.any.parent'].create({'name': 'parent'})
        child = self.env['test_orm.any.child'].create({
            'parent_id': parent.id,
            'quantity': 10,
            'tag_ids': [Command.create({'name': 'tag1'})],
        })

        self.assertEqual(self.env['test_orm.custom.table_query'].search([]).sum_quantity, 10)
        # _depends doesn't invalidate the cache of the model, should it ?
        self.env['test_orm.custom.table_query'].invalidate_model()
        child.quantity = 25
        self.assertEqual(self.env['test_orm.custom.table_query'].search([]).sum_quantity, 25)

    def test_depends_with_table_query_model_sql(self):
        parent = self.env['test_orm.any.parent'].create({'name': 'parent'})
        child = self.env['test_orm.any.child'].create({
            'parent_id': parent.id,
            'quantity': 10,
            'tag_ids': [Command.create({'name': 'tag1'})],
        })

        self.assertEqual(self.env['test_orm.custom.table_query_sql'].search([]).sum_quantity, 10)
        # _depends doesn't invalidate the cache of the model, should it ?
        self.env['test_orm.custom.table_query_sql'].invalidate_model()
        child.quantity = 25
        self.assertEqual(self.env['test_orm.custom.table_query_sql'].search([]).sum_quantity, 25)


class TestDatePartNumber(TransactionExpressionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.person = cls.env["test_orm.person"].create({"name": "that person", "birthday": "1990-02-09"})
        cls.lesson = cls.env["test_orm.lesson"].create({"teacher_id": cls.person.id, "attendee_ids": [(4, cls.person.id)]})

    def test_basic_cases(self):
        Person = self.env["test_orm.person"].with_context(active_test=False)
        with self.assertQueries(["""
            SELECT "test_orm_person"."id"
            FROM "test_orm_person"
            WHERE date_part(%s, "test_orm_person"."birthday") IN %s
            ORDER BY "test_orm_person"."id"
        """]):
            result = Person.search([('birthday.month_number', '=', '2')])
            self.assertEqual(result, self.person)

        with self.assertQueries(["""
            SELECT "test_orm_person"."id"
            FROM "test_orm_person"
            WHERE date_part(%s, "test_orm_person"."birthday") IN %s
            ORDER BY "test_orm_person"."id"
        """]):
            result = Person.search([('birthday.quarter_number', '=', '1')])
            self.assertEqual(result, self.person)

        with self.assertQueries(["""
            SELECT "test_orm_person"."id"
            FROM "test_orm_person"
            WHERE date_part(%s, "test_orm_person"."birthday") IN %s
            ORDER BY "test_orm_person"."id"
        """]):
            result = Person.search([('birthday.iso_week_number', '=', '6')])
            self.assertEqual(result, self.person)

    def test_datetime_filtered(self):
        Person = self.env["test_orm.person"].with_context(active_test=False)
        self.assertEqual(self._search(Person, [('birthday.month_number', '=', 2)]), self.person)

    def test_many2one(self):
        result = self._search(self.env["test_orm.lesson"], [('teacher_id.birthday.month_number', '=', 2)])
        self.assertEqual(result, self.lesson)

    def test_many2many(self):
        result = self._search(self.env["test_orm.lesson"], [('attendee_ids.birthday.month_number', '=', 2)])
        self.assertEqual(result, self.lesson)

    def test_related_field(self):
        result = self._search(self.env["test_orm.lesson"], [('teacher_birthdate.month_number', '=', 2)])
        self.assertEqual(result, self.lesson)

    def test_inherit(self):
        account = self.env["test_orm.person.account"].create({"person_id": self.person.id, "activation_date": "2020-03-09"})

        result = self._search(self.env["test_orm.person.account"], [('activation_date.quarter_number', '=', 1)])
        self.assertEqual(result, account)

        result = self._search(self.env["test_orm.person.account"], [('person_id.birthday.month_number', '=', 2)])
        self.assertEqual(result, account)


class TestNonIntId(TransactionCase):
    def test_query_non_int(self):
        records = self.env['test_orm.view.str.id'].search([('name', '=', 'test')])
        self.assertEqual(records.id, 'hello')
        records.invalidate_model()
        self.assertEqual(records.name, 'test')

    def test_query_non_int_read_group(self):
        result = self.env['test_orm.view.str.id'].formatted_read_group([], ['name'], ['__count'])
        self.assertEqual(result, [{'name': 'test', '__count': 1, '__extra_domain': [('name', '=', 'test')]}])
        result = self.env['test_orm.view.str.id'].formatted_read_group([], [], ['name:count'])
        self.assertEqual(result, [{'name:count': 1, '__extra_domain': [(1, '=', 1)]}])
