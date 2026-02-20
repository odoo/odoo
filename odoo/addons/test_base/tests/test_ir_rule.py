from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import tagged, TransactionCase


class Feedback(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group0 = cls.env['res.groups'].create({'name': "Group 0"})
        cls.group1 = cls.env['res.groups'].create({'name': "Group 1"})
        cls.group2 = cls.env['res.groups'].create({'name': "Group 2"})
        cls.user = cls.env['res.users'].create({
            'login': 'bob',
            'name': "Bob Bobman",
            'group_ids': [Command.set([cls.group2.id, cls.env.ref('base.group_user').id])],
        })


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestIRRuleFeedback(Feedback):
    """ Tests that proper feedback is returned on ir.rule errors
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'user_ids': [Command.link(cls.user.id)]})
        cls.model = cls.env['ir.model'].search([('model', '=', 'test_access_right.some_obj')])
        cls.record = cls.env['test_access_right.some_obj'].create({
            'val': 0,
        }).with_user(cls.user)
        cls.maxDiff = None

    def _make_rule(self, name, domain, global_=False, attr='write'):
        return self.env['ir.rule'].create({
            'name': name,
            'model_id': self.model.id,
            'groups': [] if global_ else [Command.link(self.group2.id)],
            'domain_force': domain,
            'perm_read': False,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
            'perm_' + attr: True,
        })

    def test_local(self):
        self._make_rule('rule 0', '[("val", "=", 42)]')
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description} ({self.record._name})

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )
        # debug mode
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

        ChildModel = self.env['test_access_right.inherits']
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            ChildModel.with_user(self.user).create({'some_id': self.record.id, 'val': 2})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_locals(self):
        self._make_rule('rule 0', '[("val", "=", 42)]')
        self._make_rule('rule 1', '[("val", "=", 78)]')
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0
- rule 1

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_globals_all(self):
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[("val", "=", 78)]', global_=True)
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0
- rule 1

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_globals_any(self):
        """ Global rules are AND-eded together, so when access fails it
        might be just one of the rules, and we want an exact listing
        """
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[(1, "=", 1)]', global_=True)
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_combination(self):
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[(1, "=", 1)]', global_=True)
        self._make_rule('rule 2', '[(0, "=", 1)]')
        self._make_rule('rule 3', '[("val", "=", 55)]')
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0
- rule 2
- rule 3

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_warn_company_no_access(self):
        """ If one of the failing rules mentions company_id, add a note that
        this might be a multi-company issue, but the user doesn't access to this company
        then no information about the company is shown.
        """
        self._make_rule('rule 0', "[('company_id', '=', user.company_id.id)]")
        self._make_rule('rule 1', '[("val", "=", 0)]', global_=True)
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_warn_company_no_company_field(self):
        """ If one of the failing rules mentions company_id, add a note that
        this might be a multi-company issue, but the record doesn't have company_id field
        then no information about the company is shown.
        """
        ChildModel = self.env['test_access_right.child'].sudo()
        self.env['ir.rule'].create({
            'name': 'rule 0',
            'model_id': self.env['ir.model'].search([('model', '=', ChildModel._name)]).id,
            'groups': [],
            'domain_force': '[("parent_id.company_id", "=", user.company_id.id)]',
            'perm_read': True,
        })
        self.record.sudo().company_id = self.env['res.company'].create({'name': 'Brosse Inc.'})
        self.user.sudo().company_ids = [Command.link(self.record.company_id.id)]
        child_record = ChildModel.create({'parent_id': self.record.id}).with_user(self.user)
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            _ = child_record.parent_id
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'read' access to:
- {child_record._description}, {child_record.display_name} ({child_record._name}: {child_record.id})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_warn_company_access(self):
        """ because of prefetching, read() goes through a different codepath
        to apply rules
        """
        self.record.sudo().company_id = self.env['res.company'].create({'name': 'Brosse Inc.'})
        self.user.sudo().company_ids = [Command.link(self.record.company_id.id)]
        self._make_rule('rule 0', "[('company_id', '=', user.company_id.id)]", attr='read')
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            _ = self.record.val
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'read' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id}, company={self.record.sudo().company_id.display_name})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.

This seems to be a multi-company issue, you might be able to access the record by switching to the company: {self.record.sudo().company_id.display_name}.""",
        )
        p = self.env['test_access_right.inherits'].create({'some_id': self.record.id})
        self.env.flush_all()
        self.env.invalidate_all()
        with self.assertRaisesRegex(
            AccessError,
            r"Implicitly accessed through 'Object for testing related access rights' \(test_access_right.inherits\)\.",
        ):
            p.with_user(self.user).val

    def test_warn_company_access_multi_record(self):
        """ Test that AccessError handle correctly several companies """
        company_1, company_2 = self.env['res.company'].create([
            {'name': 'Brosse Inc.'},
            {'name': 'Brosse Inc. 2'},
        ])
        records = self.env["test_access_right.some_obj"].create([
            {"val": 1, "company_id": company_1.id},
            {"val": 2, "company_id": company_2.id},
        ])
        record_1, record_2 = records
        self.user.sudo().company_ids = [Command.link(company_1.id), Command.link(company_2.id)]
        self._make_rule('rule 0', "[('company_id', '=', False)]", attr='read')
        self.env.invalidate_all()
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            _ = records.with_user(self.user).read(["val"])
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'read' access to:
- {record_1._description}, {record_1.display_name} ({record_1._name}: {record_1.id}, company={record_1.company_id.display_name})
- {record_2._description}, {record_2.display_name} ({record_2._name}: {record_2.id}, company={record_2.company_id.display_name})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.

Note: this might be a multi-company issue. Switching company may help - in Odoo, not in real life!""")

