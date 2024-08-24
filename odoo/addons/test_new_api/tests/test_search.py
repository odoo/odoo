# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import TransactionCase


class TestSubqueries(TransactionCase):
    """ Test the subqueries made by search() with relational fields. """
    maxDiff = None

    def test_and_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE ("test_new_api_multi"."partner" IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE (("res_partner"."name" LIKE %s)
                   AND ("res_partner"."phone" LIKE %s)
                )
            ))
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                ('partner.name', 'like', 'jack'),
                ('partner.phone', 'like', '01234'),
            ])

    def test_or_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE ("test_new_api_multi"."partner" IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE (("res_partner"."name" LIKE %s)
                    OR ("res_partner"."phone" LIKE %s)
                )
            ))
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                '|',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_not_and_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE (("test_new_api_multi"."partner" NOT IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE (("res_partner"."name" LIKE %s)
                    AND ("res_partner"."phone" LIKE %s)
                )
            )) OR "test_new_api_multi"."partner" IS NULL)
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                '!', '&',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_not_or_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE (("test_new_api_multi"."partner" NOT IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE (("res_partner"."name" LIKE %s)
                    OR ("res_partner"."phone" LIKE %s)
                )
            )) OR "test_new_api_multi"."partner" IS NULL)
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                '!', '|',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_or_autojoined_many2one_with_subfield(self):
        self.patch(self.env['test_new_api.multi']._fields['partner'], 'auto_join', True)
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            LEFT JOIN "res_partner" AS "test_new_api_multi__partner"
                ON ("test_new_api_multi"."partner" = "test_new_api_multi__partner"."id")
            WHERE (
                ("test_new_api_multi__partner"."name" LIKE %s)
                OR ("test_new_api_multi__partner"."phone" LIKE %s)
            )
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                '|',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_not_or_autojoined_many2one_with_subfield(self):
        self.patch(self.env['test_new_api.multi']._fields['partner'], 'auto_join', True)
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            LEFT JOIN "res_partner" AS "test_new_api_multi__partner"
                ON ("test_new_api_multi"."partner" = "test_new_api_multi__partner"."id")
            WHERE (
                "test_new_api_multi__partner"."id" IS NULL OR (
                    NOT ((
                        ("test_new_api_multi__partner"."name" LIKE %s)
                        OR ("test_new_api_multi__partner"."phone" LIKE %s)
                    ))
                )
            )
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                '!', '|',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_mixed_and_or_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE ("test_new_api_multi"."partner" IN (
                SELECT "res_partner"."id"
                FROM "res_partner"
                WHERE (
                    ("res_partner"."email" LIKE %s)
                    AND (("res_partner"."name" LIKE %s)
                      OR ("res_partner"."phone" LIKE %s)
                    )
                )
            ))
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                ('partner.email', 'like', '@sgc.us'),
                '|',
                    ('partner.name', 'like', 'jack'),
                    ('partner.phone', 'like', '01234'),
            ])

    def test_mixed_and_or_not_many2one_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE (
                (
                    (
                        ({many2one} IN (
                            {subselect} WHERE ("res_partner"."function" LIKE %s)
                        )) OR (({many2one} NOT IN (
                            {subselect} WHERE (
                                ("res_partner"."phone" LIKE %s)
                                AND ("res_partner"."mobile" LIKE %s)
                            )))
                            OR "test_new_api_multi"."partner" IS NULL
                        )
                    ) AND ({many2one} IN (
                        {subselect} WHERE (
                            ("res_partner"."name" LIKE %s)
                            OR ("res_partner"."email" LIKE %s)
                        )
                    ))
                ) AND (({many2one} NOT IN (
                    {subselect} WHERE ("res_partner"."website" LIKE %s)
                    ))
                    OR "test_new_api_multi"."partner" IS NULL
                )
            )
            ORDER BY "test_new_api_multi"."id"
        """.format(
            many2one='"test_new_api_multi"."partner"',
            subselect='SELECT "res_partner"."id" FROM "res_partner"',
        )]):
            # (function or not (phone and mobile)) and not website and (name or email)
            self.env['test_new_api.multi'].search([
                '&', '&',
                    '|',
                        ('partner.function', 'like', 'Colonel'),
                        '!', '&',
                            ('partner.phone', 'like', '+01'),
                            ('partner.mobile', 'like', '+01'),
                    '!', ('partner.website', 'like', 'sgc.us'),
                    '|',
                        ('partner.name', 'like', 'jack'),
                        ('partner.email', 'like', '@sgc.us'),
            ])

    def test_and_one2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE (("test_new_api_multi"."id" IN (
                SELECT "test_new_api_multi_line"."multi"
                FROM "test_new_api_multi_line"
                WHERE ("test_new_api_multi_line"."name" LIKE %s)
                      AND "test_new_api_multi_line"."multi" IS NOT NULL
            )) AND ("test_new_api_multi"."id" IN (
                SELECT "test_new_api_multi_line"."multi"
                FROM "test_new_api_multi_line"
                WHERE ("test_new_api_multi_line"."name" LIKE %s)
                      AND "test_new_api_multi_line"."multi" IS NOT NULL
            )))
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                ('lines.name', 'like', 'x'),
                ('lines.name', 'like', 'y'),
            ])

    def test_or_one2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE ("test_new_api_multi"."id" IN (
                SELECT "test_new_api_multi_line"."multi"
                FROM "test_new_api_multi_line"
                WHERE (("test_new_api_multi_line"."name" LIKE %s)
                    OR ("test_new_api_multi_line"."name" LIKE %s)
                ) AND "test_new_api_multi_line"."multi" IS NOT NULL
            ))
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                '|',
                    ('lines.name', 'like', 'x'),
                    ('lines.name', 'like', 'y'),
            ])

    def test_mixed_and_or_one2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE (("test_new_api_multi"."id" IN (
                SELECT "test_new_api_multi_line"."multi"
                FROM "test_new_api_multi_line"
                WHERE ("test_new_api_multi_line"."name" LIKE %s)
                   AND "test_new_api_multi_line"."multi" IS NOT NULL)
            ) AND ("test_new_api_multi"."id" IN (
                SELECT "test_new_api_multi_line"."multi"
                FROM "test_new_api_multi_line"
                WHERE (("test_new_api_multi_line"."name" LIKE %s)
                    OR ("test_new_api_multi_line"."name" LIKE %s)
                ) AND "test_new_api_multi_line"."multi" IS NOT NULL
            )))
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                ('lines.name', 'like', 'x'),
                '|',
                    ('lines.name', 'like', 'y'),
                    ('lines.name', 'like', 'z'),
            ])

    def test_and_many2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE (EXISTS (
                SELECT 1
                FROM "test_new_api_multi_test_new_api_multi_tag_rel" AS "test_new_api_multi__tags"
                WHERE "test_new_api_multi__tags"."test_new_api_multi_id" = "test_new_api_multi"."id"
                AND "test_new_api_multi__tags"."test_new_api_multi_tag_id" IN (
                    SELECT "test_new_api_multi_tag"."id"
                    FROM "test_new_api_multi_tag"
                    WHERE (
                        ("test_new_api_multi_tag"."name" ILIKE %s)
                        AND ("test_new_api_multi_tag"."name" LIKE %s)
                    )
                )
            ) AND EXISTS (
                SELECT 1
                FROM "test_new_api_multi_test_new_api_multi_tag_rel" AS "test_new_api_multi__tags"
                WHERE "test_new_api_multi__tags"."test_new_api_multi_id" = "test_new_api_multi"."id"
                AND "test_new_api_multi__tags"."test_new_api_multi_tag_id" IN (
                    SELECT "test_new_api_multi_tag"."id"
                    FROM "test_new_api_multi_tag"
                    WHERE (
                        ("test_new_api_multi_tag"."name" ILIKE %s)
                        AND ("test_new_api_multi_tag"."name" LIKE %s)
                    )
                )
            ))
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                ('tags.name', 'like', 'x'),
                ('tags.name', 'like', 'y'),
            ])

    def test_or_many2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE EXISTS (
                SELECT 1
                FROM "test_new_api_multi_test_new_api_multi_tag_rel" AS "test_new_api_multi__tags"
                WHERE "test_new_api_multi__tags"."test_new_api_multi_id" = "test_new_api_multi"."id"
                AND "test_new_api_multi__tags"."test_new_api_multi_tag_id" IN (
                    SELECT "test_new_api_multi_tag"."id"
                    FROM "test_new_api_multi_tag"
                    WHERE (
                        ("test_new_api_multi_tag"."name" ILIKE %s)
                        AND (
                            ("test_new_api_multi_tag"."name" LIKE %s)
                            OR ("test_new_api_multi_tag"."name" LIKE %s)
                        )
                    )
                )
            )
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                '|',
                    ('tags.name', 'like', 'x'),
                    ('tags.name', 'like', 'y'),
            ])

    def test_mixed_and_or_many2many_with_subfield(self):
        with self.assertQueries(["""
            SELECT "test_new_api_multi"."id"
            FROM "test_new_api_multi"
            WHERE (
                EXISTS (
                    SELECT 1
                    FROM "test_new_api_multi_test_new_api_multi_tag_rel" AS "test_new_api_multi__tags"
                    WHERE "test_new_api_multi__tags"."test_new_api_multi_id" = "test_new_api_multi"."id"
                    AND "test_new_api_multi__tags"."test_new_api_multi_tag_id" IN (
                        SELECT "test_new_api_multi_tag"."id"
                        FROM "test_new_api_multi_tag"
                        WHERE (
                            ("test_new_api_multi_tag"."name" ILIKE %s)
                            AND ("test_new_api_multi_tag"."name" LIKE %s)
                        )
                    )
                ) AND EXISTS (
                    SELECT 1
                    FROM "test_new_api_multi_test_new_api_multi_tag_rel" AS "test_new_api_multi__tags"
                    WHERE "test_new_api_multi__tags"."test_new_api_multi_id" = "test_new_api_multi"."id"
                    AND "test_new_api_multi__tags"."test_new_api_multi_tag_id" IN (
                        SELECT "test_new_api_multi_tag"."id"
                        FROM "test_new_api_multi_tag"
                        WHERE (
                            ("test_new_api_multi_tag"."name" ILIKE %s)
                            AND (
                                ("test_new_api_multi_tag"."name" LIKE %s)
                                OR ("test_new_api_multi_tag"."name" LIKE %s)
                            )
                        )
                    )
                )
            )
            ORDER BY "test_new_api_multi"."id"
        """]):
            self.env['test_new_api.multi'].search([
                ('tags.name', 'like', 'x'),
                '|',
                    ('tags.name', 'like', 'y'),
                    ('tags.name', 'like', 'z'),
            ])

    def test_related_simple(self):
        model = self.env['test_new_api.related'].with_user(self.env.ref('base.user_admin'))
        self.env['ir.rule'].create({
            'name': 'related_foo',
            'model_id': self.env['ir.model']._get('test_new_api.related_foo').id,
            'domain_force': "[('id', '<', 1000)]",
        })

        # warmup
        model.search([('foo_name', '=', 'a')])
        model.search([('foo_name_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."name" = %s)
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_name_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."name" = %s)
                AND ("test_new_api_related_foo"."id" < %s)
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_name', '=', 'a')])

    def test_related_multi(self):
        model = self.env['test_new_api.related'].with_user(self.env.ref('base.user_admin'))
        self.env['ir.rule'].create({
            'name': 'related_foo',
            'model_id': self.env['ir.model']._get('test_new_api.related_foo').id,
            'domain_force': "[('id', '<', 1000)]",
        })
        self.env['ir.rule'].create({
            'name': 'related_bar',
            'model_id': self.env['ir.model']._get('test_new_api.related_bar').id,
            'domain_force': "[('id', '<', 1000)]",
        })

        # warmup
        model.search([('foo_bar_name', '=', 'a')])
        model.search([('foo_bar_name_sudo', '=', 'a')])
        model.search([('foo_id_bar_name', '=', 'a')])
        model.search([('foo_bar_id_name', '=', 'a')])
        model.search([('foo_bar_sudo_id_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."bar_id" IN (
                    SELECT "test_new_api_related_bar"."id"
                    FROM "test_new_api_related_bar"
                    WHERE ("test_new_api_related_bar"."name" = %s)
                ))
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_bar_name_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."bar_id" IN (
                    SELECT "test_new_api_related_bar"."id"
                    FROM "test_new_api_related_bar"
                    WHERE ("test_new_api_related_bar"."name" = %s)
                    AND ("test_new_api_related_bar"."id" < %s)
                ))
                AND ("test_new_api_related_foo"."id" < %s)
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_bar_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."bar_id" IN (
                    SELECT "test_new_api_related_bar"."id"
                    FROM "test_new_api_related_bar"
                    WHERE ("test_new_api_related_bar"."name" = %s)
                    AND ("test_new_api_related_bar"."id" < %s)
                ))
                AND ("test_new_api_related_foo"."id" < %s)
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_id_bar_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."bar_id" IN (
                    SELECT "test_new_api_related_bar"."id"
                    FROM "test_new_api_related_bar"
                    WHERE ("test_new_api_related_bar"."name" = %s)
                    AND ("test_new_api_related_bar"."id" < %s)
                ))
                AND ("test_new_api_related_foo"."id" < %s)
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_bar_id_name', '=', 'a')])

        # bypass security for foo_id.bar_id, but not for name
        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."bar_id" IN (
                    SELECT "test_new_api_related_bar"."id"
                    FROM "test_new_api_related_bar"
                    WHERE ("test_new_api_related_bar"."name" = %s)
                    AND ("test_new_api_related_bar"."id" < %s)
                ))
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_bar_sudo_id_name', '=', 'a')])

    def test_related_null(self):
        model = self.env['test_new_api.related']

        # warmup
        model.search([('foo_name', '=', 'a')])
        model.search([('foo_name', '!=', 'a')])
        model.search([('foo_name', '=', False)])
        model.search([('foo_name', '!=', False)])
        model.search([('foo_name', 'in', ['a', 'b'])])
        model.search([('foo_name', 'not in', ['a', 'b'])])
        model.search([('foo_name', 'in', ['a', False])])
        model.search([('foo_name', 'not in', ['a', False])])
        model.search([('foo_bar_name', '=', False)])
        model.search([('foo_bar_name', '!=', False)])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."name" = %s)
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE (
                ("test_new_api_related"."foo_id" IN (
                    SELECT "test_new_api_related_foo"."id"
                    FROM "test_new_api_related_foo"
                    WHERE (
                        ("test_new_api_related_foo"."name" != %s)
                        OR "test_new_api_related_foo"."name" IS NULL
                    )
                ))
                OR "test_new_api_related"."foo_id" IS NULL
            )
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_name', '!=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE (
                ("test_new_api_related"."foo_id" IN (
                    SELECT "test_new_api_related_foo"."id"
                    FROM "test_new_api_related_foo"
                    WHERE (("test_new_api_related_foo"."name" = %s) OR "test_new_api_related_foo"."name" IS NULL)
                ))
                OR "test_new_api_related"."foo_id" IS NULL
            )
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_name', '=', False)])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."name" != %s)
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_name', '!=', False)])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."name" IN %s)
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_name', 'in', ['a', 'b'])])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE (
                ("test_new_api_related"."foo_id" IN (
                    SELECT "test_new_api_related_foo"."id"
                    FROM "test_new_api_related_foo"
                    WHERE (
                        ("test_new_api_related_foo"."name" NOT IN %s)
                        OR "test_new_api_related_foo"."name" IS NULL
                    )
                ))
                OR "test_new_api_related"."foo_id" IS NULL
            )
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_name', 'not in', ['a', 'b'])])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE (
                ("test_new_api_related"."foo_id" IN (
                    SELECT "test_new_api_related_foo"."id"
                    FROM "test_new_api_related_foo"
                    WHERE (
                        ("test_new_api_related_foo"."name" IN %s)
                        OR "test_new_api_related_foo"."name" IS NULL
                    )
                ))
                OR "test_new_api_related"."foo_id" IS NULL
            )
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_name', 'in', ['a', False])])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE (
                    ("test_new_api_related_foo"."name" NOT IN %s)
                    AND "test_new_api_related_foo"."name" IS NOT NULL
                )
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_name', 'not in', ['a', False])])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE (
                ("test_new_api_related"."foo_id" IN (
                    SELECT "test_new_api_related_foo"."id"
                    FROM "test_new_api_related_foo"
                    WHERE (
                        ("test_new_api_related_foo"."bar_id" IN (
                            SELECT "test_new_api_related_bar"."id"
                            FROM "test_new_api_related_bar"
                            WHERE (("test_new_api_related_bar"."name" = %s) OR "test_new_api_related_bar"."name" IS NULL)
                        ))
                        OR "test_new_api_related_foo"."bar_id" IS NULL
                    )
                ))
                OR "test_new_api_related"."foo_id" IS NULL
            )
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_bar_name', '=', False)])

        with self.assertQueries(["""
            SELECT "test_new_api_related"."id"
            FROM "test_new_api_related"
            WHERE ("test_new_api_related"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."bar_id" IN (
                    SELECT "test_new_api_related_bar"."id"
                    FROM "test_new_api_related_bar"
                    WHERE ("test_new_api_related_bar"."name" != %s)
                ))
            ))
            ORDER BY "test_new_api_related"."id"
        """]):
            model.search([('foo_bar_name', '!=', False)])

    def test_related_inherited(self):
        model = self.env['test_new_api.related_inherits'].with_user(self.env.ref('base.user_admin'))
        self.env['ir.rule'].create({
            'name': 'related',
            'model_id': self.env['ir.model']._get('test_new_api.related').id,
            'domain_force': "[('id', '<', 1000)]",
        })
        self.env['ir.rule'].create({
            'name': 'related_foo',
            'model_id': self.env['ir.model']._get('test_new_api.related_foo').id,
            'domain_force': "[('id', '<', 1000)]",
        })
        self.env['ir.rule'].create({
            'name': 'related_bar',
            'model_id': self.env['ir.model']._get('test_new_api.related_bar').id,
            'domain_force': "[('id', '<', 1000)]",
        })

        # warmup
        model.search([('name', '=', 'a')])
        model.search([('foo_name', '=', 'a')])
        model.search([('foo_name_sudo', '=', 'a')])
        model.search([('foo_bar_name', '=', 'a')])
        model.search([('foo_bar_name_sudo', '=', 'a')])

        # search on inherited fields
        with self.assertQueries(["""
            SELECT "test_new_api_related_inherits"."id"
            FROM "test_new_api_related_inherits"
            LEFT JOIN "test_new_api_related" AS "test_new_api_related_inherits__base_id"
                ON ("test_new_api_related_inherits"."base_id" = "test_new_api_related_inherits__base_id"."id")
            WHERE ("test_new_api_related_inherits__base_id"."name" = %s)
            AND ("test_new_api_related_inherits__base_id"."id" < %s)
            ORDER BY "test_new_api_related_inherits"."id"
        """]):
            model.search([('name', '=', 'a')])

        # search on inherited related fields
        with self.assertQueries(["""
            SELECT "test_new_api_related_inherits"."id"
            FROM "test_new_api_related_inherits"
            LEFT JOIN "test_new_api_related" AS "test_new_api_related_inherits__base_id"
                ON ("test_new_api_related_inherits"."base_id" = "test_new_api_related_inherits__base_id"."id")
            WHERE ("test_new_api_related_inherits__base_id"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."name" = %s)
            ))
            AND ("test_new_api_related_inherits__base_id"."id" < %s)
            ORDER BY "test_new_api_related_inherits"."id"
        """]):
            model.search([('foo_name_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related_inherits"."id"
            FROM "test_new_api_related_inherits"
            LEFT JOIN "test_new_api_related" AS "test_new_api_related_inherits__base_id"
                ON ("test_new_api_related_inherits"."base_id" = "test_new_api_related_inherits__base_id"."id")
            WHERE ("test_new_api_related_inherits__base_id"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."name" = %s)
                AND ("test_new_api_related_foo"."id" < %s)
            ))
            AND ("test_new_api_related_inherits__base_id"."id" < %s)
            ORDER BY "test_new_api_related_inherits"."id"
        """]):
            model.search([('foo_name', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related_inherits"."id"
            FROM "test_new_api_related_inherits"
            LEFT JOIN "test_new_api_related" AS "test_new_api_related_inherits__base_id"
                ON ("test_new_api_related_inherits"."base_id" = "test_new_api_related_inherits__base_id"."id")
            WHERE ("test_new_api_related_inherits__base_id"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."bar_id" IN (
                    SELECT "test_new_api_related_bar"."id"
                    FROM "test_new_api_related_bar"
                    WHERE ("test_new_api_related_bar"."name" = %s)
                ))
            ))
            AND ("test_new_api_related_inherits__base_id"."id" < %s)
            ORDER BY "test_new_api_related_inherits"."id"
        """]):
            model.search([('foo_bar_name_sudo', '=', 'a')])

        with self.assertQueries(["""
            SELECT "test_new_api_related_inherits"."id"
            FROM "test_new_api_related_inherits"
            LEFT JOIN "test_new_api_related" AS "test_new_api_related_inherits__base_id"
                ON ("test_new_api_related_inherits"."base_id" = "test_new_api_related_inherits__base_id"."id")
            WHERE ("test_new_api_related_inherits__base_id"."foo_id" IN (
                SELECT "test_new_api_related_foo"."id"
                FROM "test_new_api_related_foo"
                WHERE ("test_new_api_related_foo"."bar_id" IN (
                    SELECT "test_new_api_related_bar"."id"
                    FROM "test_new_api_related_bar"
                    WHERE ("test_new_api_related_bar"."name" = %s)
                    AND ("test_new_api_related_bar"."id" < %s)
                ))
                AND ("test_new_api_related_foo"."id" < %s)
            ))
            AND ("test_new_api_related_inherits__base_id"."id" < %s)
            ORDER BY "test_new_api_related_inherits"."id"
        """]):
            model.search([('foo_bar_name', '=', 'a')])


class TestFlushSearch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env['test_new_api.city']
        cls.belgium, cls.france = cls.env['test_new_api.country'].create([
            {'name': 'Belgium'}, {'name': 'France'},
        ])
        cls.brussels, cls.paris = cls.env['test_new_api.city'].create([
            {'name': "Brussels", 'country_id': cls.belgium.id},
            {'name': "Paris", 'country_id': cls.france.id},
        ])

    def test_flush_fields_in_domain(self):
        with self.assertQueries(['''
            UPDATE "test_new_api_city"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_new_api_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_city"."id"
            FROM "test_new_api_city"
            WHERE ("test_new_api_city"."name" LIKE %s)
            ORDER BY "test_new_api_city"."id"
        ''']):
            self.brussels.name = "Bruxelles"
            self.model.search([('name', 'like', 'foo')], order='id')

    def test_flush_fields_in_subdomain(self):
        with self.assertQueries(['''
            UPDATE "test_new_api_city"
            SET "country_id" = "__tmp"."country_id"::int4,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "country_id", "write_date", "write_uid")
            WHERE "test_new_api_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_city"."id"
            FROM "test_new_api_city"
            WHERE ("test_new_api_city"."country_id" IN (
                SELECT "test_new_api_country"."id"
                FROM "test_new_api_country"
                WHERE ("test_new_api_country"."name" LIKE %s)
            ))
            ORDER BY "test_new_api_city"."id"
        ''']):
            self.brussels.country_id = self.france
            self.model.search([('country_id.name', 'like', 'foo')], order='id')

        with self.assertQueries(['''
            UPDATE "test_new_api_country"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_new_api_country"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_city"."id"
            FROM "test_new_api_city"
            WHERE ("test_new_api_city"."country_id" IN (
                SELECT "test_new_api_country"."id"
                FROM "test_new_api_country"
                WHERE ("test_new_api_country"."name" LIKE %s)
            ))
            ORDER BY "test_new_api_city"."id"
        ''']):
            self.belgium.name = "Belgique"
            self.model.search([('country_id.name', 'like', 'foo')], order='id')

    def test_flush_auto_join_field_in_domain(self):
        self.patch(type(self.brussels).country_id, 'auto_join', True)

        with self.assertQueries(['''
            UPDATE "test_new_api_city"
            SET "country_id" = "__tmp"."country_id"::int4,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "country_id", "write_date", "write_uid")
            WHERE "test_new_api_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_city"."id"
            FROM "test_new_api_city"
            LEFT JOIN "test_new_api_country" AS "test_new_api_city__country_id"
                ON ("test_new_api_city"."country_id" = "test_new_api_city__country_id"."id")
            WHERE ("test_new_api_city__country_id"."name" LIKE %s)
            ORDER BY "test_new_api_city"."id"
        ''']):
            self.brussels.country_id = self.france
            self.model.search([('country_id.name', 'like', 'foo')], order='id')

    def test_flush_inherited_field_in_domain(self):
        payment = self.env['test_new_api.payment'].create({})
        move = self.env['test_new_api.move'].create({})

        with self.assertQueries(['''
            UPDATE "test_new_api_payment"
            SET "move_id" = "__tmp"."move_id"::int4,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "move_id", "write_date", "write_uid")
            WHERE "test_new_api_payment"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_payment"."id"
            FROM "test_new_api_payment"
            LEFT JOIN "test_new_api_move" AS "test_new_api_payment__move_id"
                ON ("test_new_api_payment"."move_id" = "test_new_api_payment__move_id"."id")
            WHERE ("test_new_api_payment__move_id"."tag_repeat" > %s)
            ORDER BY "test_new_api_payment"."id"
        ''']):
            payment.move_id = move
            payment.search([('tag_repeat', '>', 0)], order='id')

        with self.assertQueries(['''
            UPDATE "test_new_api_move"
            SET "tag_repeat" = "__tmp"."tag_repeat"::int4,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "tag_repeat", "write_date", "write_uid")
            WHERE "test_new_api_move"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_payment"."id"
            FROM "test_new_api_payment"
            LEFT JOIN "test_new_api_move" AS "test_new_api_payment__move_id"
                ON ("test_new_api_payment"."move_id" = "test_new_api_payment__move_id"."id")
            WHERE ("test_new_api_payment__move_id"."tag_repeat" > %s)
            ORDER BY "test_new_api_payment"."id"
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
            UPDATE "test_new_api_city"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_new_api_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_city"."id"
            FROM "test_new_api_city"
            WHERE ("test_new_api_city"."id" = %s) AND ("test_new_api_city"."name" LIKE %s)
            ORDER BY "test_new_api_city"."id"
        ''']):
            self.brussels.name = "Bruxelles"
            model.search([('id', '=', self.paris.id)], order='id')

    def test_flush_fields_in_order(self):
        with self.assertQueries(['''
            UPDATE "test_new_api_city"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_new_api_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_city"."id"
            FROM "test_new_api_city"
            WHERE ("test_new_api_city"."id" = %s)
            ORDER BY "test_new_api_city"."name", "test_new_api_city"."id"
        ''']):
            self.brussels.name = "Bruxelles"
            self.model.search([('id', '=', self.paris.id)], order='name, id')

        # test indirect fields, when ordering by many2one field
        with self.assertQueries(['''
            UPDATE "test_new_api_country"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_new_api_country"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_city"."id"
            FROM "test_new_api_city"
            LEFT JOIN "test_new_api_country" AS "test_new_api_city__country_id"
                ON ("test_new_api_city"."country_id" = "test_new_api_city__country_id"."id")
            WHERE ("test_new_api_city"."id" = %s)
            ORDER BY "test_new_api_city__country_id"."name",
                    "test_new_api_city__country_id"."id",
                    "test_new_api_city"."id"
        ''']):
            self.belgium.name = "Belgique"
            self.model.search([('id', '=', self.paris.id)], order='country_id, id')

        with self.assertQueries(['''
            UPDATE "test_new_api_city"
            SET "country_id" = "__tmp"."country_id"::int4,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "country_id", "write_date", "write_uid")
            WHERE "test_new_api_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_city"."id"
            FROM "test_new_api_city"
            LEFT JOIN "test_new_api_country" AS "test_new_api_city__country_id"
                ON ("test_new_api_city"."country_id" = "test_new_api_city__country_id"."id")
            WHERE ("test_new_api_city"."id" = %s)
            ORDER BY "test_new_api_city__country_id"."name",
                    "test_new_api_city__country_id"."id",
                    "test_new_api_city"."id"
        ''']):
            self.brussels.country_id = self.france
            self.model.search([('id', '=', self.paris.id)], order='country_id, id')

    def test_do_not_flush_fields_to_fetch(self):
        with self.assertQueries(['''
            SELECT "test_new_api_city"."id", "test_new_api_city"."name"
            FROM "test_new_api_city"
            WHERE ("test_new_api_city"."id" = %s)
            ORDER BY "test_new_api_city"."id"
        '''], flush=False):
            self.brussels.name = "Bruxelles"
            self.model.search_fetch([('id', '=', self.brussels.id)], ['name'], order='id')

        # except when the field appears in another clause
        with self.assertQueries(['''
            UPDATE "test_new_api_city"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_new_api_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_city"."id", "test_new_api_city"."name"
            FROM "test_new_api_city"
            WHERE ("test_new_api_city"."name" LIKE %s)
            ORDER BY "test_new_api_city"."id"
        '''], flush=False):
            self.brussels.name = "Brussel"
            self.model.search_fetch([('name', 'like', 'Brussel')], ['name'], order='id')

        with self.assertQueries(['''
            UPDATE "test_new_api_city"
            SET "name" = "__tmp"."name"::VARCHAR,
                "write_date" = "__tmp"."write_date"::timestamp,
                "write_uid" = "__tmp"."write_uid"::int4
            FROM (VALUES %s) AS "__tmp"("id", "name", "write_date", "write_uid")
            WHERE "test_new_api_city"."id" = "__tmp"."id"
        ''', '''
            SELECT "test_new_api_city"."id", "test_new_api_city"."name"
            FROM "test_new_api_city"
            WHERE ("test_new_api_city"."id" = %s)
            ORDER BY "test_new_api_city"."name"
        '''], flush=False):
            self.brussels.name = "Brüsel"
            self.model.search_fetch([('id', '=', self.brussels.id)], ['name'], order='name')

    def test_depends_with_view_model(self):
        parent = self.env['test_new_api.any.parent'].create({'name': 'parent'})
        child = self.env['test_new_api.any.child'].create({
            'parent_id': parent.id,
            'quantity': 10,
            'tag_ids': [Command.create({'name': 'tag1'})]
        })

        self.assertEqual(self.env['test_new_api.custom.view'].search([]).sum_quantity, 10)
        # _depends doesn't invalidate the cache of the model, should it ?
        self.env['test_new_api.custom.view'].invalidate_model()
        child.quantity = 25
        self.assertEqual(self.env['test_new_api.custom.view'].search([]).sum_quantity, 25)

    def test_depends_with_table_query_model(self):
        parent = self.env['test_new_api.any.parent'].create({'name': 'parent'})
        child = self.env['test_new_api.any.child'].create({
            'parent_id': parent.id,
            'quantity': 10,
            'tag_ids': [Command.create({'name': 'tag1'})]
        })

        self.assertEqual(self.env['test_new_api.custom.table_query'].search([]).sum_quantity, 10)
        # _depends doesn't invalidate the cache of the model, should it ?
        self.env['test_new_api.custom.table_query'].invalidate_model()
        child.quantity = 25
        self.assertEqual(self.env['test_new_api.custom.table_query'].search([]).sum_quantity, 25)

    def test_depends_with_table_query_model_sql(self):
        parent = self.env['test_new_api.any.parent'].create({'name': 'parent'})
        child = self.env['test_new_api.any.child'].create({
            'parent_id': parent.id,
            'quantity': 10,
            'tag_ids': [Command.create({'name': 'tag1'})]
        })

        self.assertEqual(self.env['test_new_api.custom.table_query_sql'].search([]).sum_quantity, 10)
        # _depends doesn't invalidate the cache of the model, should it ?
        self.env['test_new_api.custom.table_query_sql'].invalidate_model()
        child.quantity = 25
        self.assertEqual(self.env['test_new_api.custom.table_query_sql'].search([]).sum_quantity, 25)


class TestDatePartNumber(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.person = cls.env["test_new_api.person"].create({"name": "that person", "birthday": "1990-02-09"})
        cls.lesson = cls.env["test_new_api.lesson"].create({"teacher_id": cls.person.id, "attendee_ids": [(4, cls.person.id)]})

    def test_basic_cases(self):
        with self.assertQueries(["""
            SELECT "test_new_api_person"."id"
            FROM "test_new_api_person"
            WHERE date_part(%s, "test_new_api_person"."birthday") = %s
            ORDER BY "test_new_api_person"."id"
        """]):
            result = self.env["test_new_api.person"].search([('birthday.month_number', '=', '2')])
            self.assertEqual(result, self.person)

        with self.assertQueries(["""
            SELECT "test_new_api_person"."id"
            FROM "test_new_api_person"
            WHERE date_part(%s, "test_new_api_person"."birthday") = %s
            ORDER BY "test_new_api_person"."id"
        """]):
            result = self.env["test_new_api.person"].search([('birthday.quarter_number', '=', '1')])
            self.assertEqual(result, self.person)

        with self.assertQueries(["""
            SELECT "test_new_api_person"."id"
            FROM "test_new_api_person"
            WHERE date_part(%s, "test_new_api_person"."birthday") = %s
            ORDER BY "test_new_api_person"."id"
        """]):
            result = self.env["test_new_api.person"].search([('birthday.iso_week_number', '=', '6')])
            self.assertEqual(result, self.person)

    def test_many2one(self):
        result = self.env["test_new_api.lesson"].search([('teacher_id.birthday.month_number', '=', 2)])
        self.assertEqual(result, self.lesson)

    def test_many2many(self):
        result = self.env["test_new_api.lesson"].search([('attendee_ids.birthday.month_number', '=', 2)])
        self.assertEqual(result, self.lesson)

    def test_related_field(self):
        result = self.env["test_new_api.lesson"].search([('teacher_birthdate.month_number', '=', 2)])
        self.assertEqual(result, self.lesson)

    def test_inherit(self):
        account = self.env["test_new_api.person.account"].create({"person_id": self.person.id, "activation_date": "2020-03-09"})

        result = self.env["test_new_api.person.account"].search([('activation_date.quarter_number', '=', 1)])
        self.assertEqual(result, account)

        result = self.env["test_new_api.person.account"].search([('person_id.birthday.month_number', '=', 2)])
        self.assertEqual(result, account)
