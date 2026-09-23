from odoo.tests import TransactionCase


class One2manyReadGroupingCase(TransactionCase):
    def _assert_matches_the_descriptor(self, records, fname):
        field = records._fields[fname]
        inverse = records.env[field.comodel_name]._fields[field.inverse_name]
        self.env.invalidate_all()
        from_cache = {r.id: r[fname].ids for r in records}
        self.env.invalidate_all()
        one_by_one = {}
        for record in records:
            lines = record.env[field.comodel_name].search(
                field.get_comodel_domain(record)
                & records.env.registry.access_policy.record_domain(
                    records.env, field.comodel_name, "read"
                )
            )
            one_by_one[record.id] = [
                line.id
                for line in lines
                if (
                    line[inverse.name].id if inverse.is_many2one else line[inverse.name]
                )
                == record.id
            ]
        self.assertEqual(from_cache, one_by_one, f"{fname} grouped differently")

    def test_a_stored_many2one_inverse(self):
        parent = self.env["test_orm.multi"].create({})
        self.env["test_orm.multi.line"].create(
            [{"multi": parent.id, "name": f"l{i}"} for i in range(5)]
        )
        self.env.flush_all()
        self._assert_matches_the_descriptor(parent, "lines")

    def test_a_many2one_reference_inverse(self):
        host = self.env["test_orm.inverse_m2o_ref"].create({})
        self.env["test_orm.model_many2one_reference"].create(
            [
                {"res_model": "test_orm.inverse_m2o_ref", "res_id": host.id}
                for _ in range(4)
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(len(host.model_ids), 4)
        self.env.invalidate_all()
        self._assert_matches_the_descriptor(host, "model_ids")

    def test_a_non_stored_computed_inverse(self):
        user = self.env.user
        discussion = self.env["test_orm.discussion"].create(
            {"name": "d", "participants": [(4, user.id)]}
        )
        self.env["test_orm.emailmessage"].create(
            [
                {
                    "discussion": discussion.id,
                    "body": f"b{i}",
                    "author": user.id,
                    "email_to": f"x{i}@example.com",
                }
                for i in range(4)
            ]
        )
        self.env.flush_all()
        inverse = self.env["test_orm.emailmessage"]._fields["discussion"]
        self.assertFalse(
            inverse.store,
            "test premise: this inverse must be non-stored, so search_fetch "
            "cannot fill its cache and the fallback is what runs",
        )
        self.env.invalidate_all()
        self.assertEqual(len(discussion.emails), 4)
        self.env.invalidate_all()
        self._assert_matches_the_descriptor(discussion, "emails")

    def test_lines_keep_their_order(self):
        parent = self.env["test_orm.multi"].create({})
        lines = self.env["test_orm.multi.line"].create(
            [{"multi": parent.id, "name": f"l{i}"} for i in range(6)]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        comodel = self.env["test_orm.multi.line"]
        expected = comodel.search([("multi", "=", parent.id)]).ids
        self.assertEqual(parent.lines.ids, expected)
        self.assertEqual(sorted(parent.lines.ids), sorted(lines.ids))
