from odoo.fields import Command
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class Many2manyCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.ship = self.env['test_orm.ship'].create({'name': 'Colombus'})
        # the ship contains one prisoner
        self.env['test_orm.prisoner'].create({
            'name': 'Brian',
            'ship_ids': self.ship.ids,
        })
        # the ship contains one pirate
        self.blackbeard = self.env['test_orm.pirate'].create({
            'name': 'Black Beard',
            'ship_ids': self.ship.ids,
        })
        self.redbeard = self.env['test_orm.pirate'].create({'name': 'Red Beard'})

    def test_not_in_relation(self):
        pirates = self.env['test_orm.pirate'].search([('ship_ids', 'not in', self.ship.ids)])
        self.assertEqual(len(pirates), 1)
        self.assertEqual(pirates, self.redbeard)

    def test_not_in_relation_as_query(self):
        # ship_ids is a Query object
        ship_ids = self.env['test_orm.ship']._search([('name', '=', 'Colombus')])
        pirates = self.env['test_orm.pirate'].search([('ship_ids', 'not in', ship_ids)])
        self.assertEqual(len(pirates), 1)
        self.assertEqual(pirates, self.redbeard)

    def test_attachment_m2m_link(self):
        user = new_test_user(self.env, 'foo', groups='base.group_system')

        attachments = self.env['ir.attachment'].create({
            'res_model': self.ship._name,
            'res_id': self.ship.id,
            'name': 'test',
        }).with_user(user)
        record = self.env['test_orm.attachment.host'].create({
            'real_binary': 'aGV5',
        }).with_user(user)
        attachments += attachments.sudo().search([
            ('res_model', '=', record._name),
            ('res_field', '=', 'real_binary'),
        ])
        self.assertEqual(len(attachments), 2)
        record.real_m2m_attachment_ids = [Command.link(a.id) for a in attachments]

        self.assertFalse(record.env.su)

        record.invalidate_model()
        self.assertEqual(len(record.real_m2m_attachment_ids), len(attachments))

    def test_bypass_search_access(self):
        user = new_test_user(self.env, 'foo', groups='base.group_system')

        attachment = self.env['test_orm.attachment'].create({
            'res_model': self.ship._name,
            'res_id': self.ship.id,
        }).with_user(user)
        self.env['ir.access'].create({
            'name': "No access",
            'model_id': self.env['ir.model']._get(attachment._name).id,
            'operation': 'crud',
            'domain': str([(0, '=', 1)]),
        })
        record = self.env['test_orm.attachment.host'].create({
            'm2m_attachment_ids': [Command.link(attachment.id)],
        }).with_user(user)

        self.assertFalse(attachment.has_access('read'))
        self.assertFalse(record.env.su)
        field = record._fields['m2m_attachment_ids']
        self.assertTrue(field.bypass_search_access)

        # attachments are always searched in sudo and filtered on record access
        self.assertEqual(record.m2m_attachment_ids, attachment)

        # check that otherwise, attachments are filtered
        self.patch(field, 'bypass_search_access', False)
        self.assertEqual(record.m2m_attachment_ids, attachment.browse())

    def test_non_stored_many2many_write_keeps_previous_values(self):
        user = new_test_user(self.env, 'non_stored_m2m_user')
        tag1, tag2 = self.env['test_orm.multi.tag'].create([{'name': 'Tag 1'}, {'name': 'Tag 2'}])
        record = self.env['test_orm.non_stored_m2m'].create({}).with_user(user)

        record.write({'tag_ids': [Command.link(tag1.id)]})
        self.env.invalidate_all()
        self.assertEqual(record.tag_ids, tag1)

        record.write({'tag_ids': [Command.link(tag2.id)]})
        self.env.invalidate_all()
        self.assertEqual(record.tag_ids, tag1 + tag2)

    def test_commands_inactive(self):
        """
        Check the behaviour of LINK, UNLINK, and CLEAR commands for many2many fields.
        If this test is broken the optimization for _load_records (see must_update)
        may be broken.
        """
        def create_data(linked):
            bar = self.env['test_orm.related_bar'].create({})
            bar.active = False
            foo = self.env['test_orm.related_foo'].create({'bar_ids': [Command.link(bar.id)] if linked else False})
            self.assertEqual(foo.bar_ids.ids, [])
            self.assertEqual(foo.with_context(active_test=False).bar_ids.ids, [bar.id] if linked else [])
            return foo, bar

        fname = 'bar_ids'
        field = self.env['test_orm.related_foo']._fields[fname]

        # Ensure that LINK command ADDS inactive records
        foo, bar = create_data(True)
        # convert_to_cache with field values does not include inactive records
        self.assertEqual(field.convert_to_cache(foo[fname], foo), ())
        # we can get the inactive records explicitly
        self.assertEqual(field.convert_to_cache(foo.with_context(active_test=False)[fname], foo), (bar.id,))
        commands = [Command.link(bar.id)]
        # convert_to_cache with LINK command includes inactive records
        self.assertEqual(field.convert_to_cache(commands, foo), (bar.id,))
        # The right way to compare them
        self.assertEqual(
            field.convert_to_cache(foo.with_context(active_test=False)[fname], foo),
            field.convert_to_cache(commands, foo),
        )
        # Running the commands and checking the result
        foo[fname] = commands
        foo.invalidate_recordset()
        self.assertEqual(foo.bar_ids.ids, [])
        self.assertEqual(foo.with_context(active_test=False).bar_ids.ids, [bar.id])

        # Ensure that UNLINK command does NOT remove inactive records
        foo, bar = create_data(True)
        commands = [Command.unlink(bar.id)]
        # Running the commands and checking the result
        foo[fname] = commands
        foo.invalidate_recordset()
        self.assertEqual(foo.bar_ids.ids, [])
        self.assertEqual(foo.with_context(active_test=False).bar_ids.ids, [bar.id])

        # Ensure that CLEAR command does NOT remove inactive records
        foo, bar = create_data(True)
        commands = [Command.clear()]
        # Running the commands and checking the result
        foo[fname] = commands
        foo.invalidate_recordset()
        self.assertEqual(foo.bar_ids.ids, [])
        self.assertEqual(foo.with_context(active_test=False).bar_ids.ids, [bar.id])

    def test_load_records_skip_write(self):
        """ _load_records() does not write values that are sure to not change. """
        Foo = self.env['test_orm.related_foo']
        Bar = self.env['test_orm.related_bar']
        written = []
        origin = self.registry['test_orm.related_foo']._load_records_write

        def _load_records_write(self, values):
            written.append(dict(values))
            return origin(self, values)

        self.patch(self.registry['test_orm.related_foo'], '_load_records_write', _load_records_write)

        bar, inactive_bar = Bar.create([{'name': 'a'}, {'name': 'b', 'active': False}])
        foo = Foo.create({'name': 'foo', 'bar_ids': [Command.link(bar.id), Command.link(inactive_bar.id)]})
        self.env['ir.model.data'].create({
            'module': '__test__', 'name': 'foo', 'model': Foo._name, 'res_id': foo.id,
        })

        def load(values):
            written.clear()
            Foo._load_records([{'xml_id': '__test__.foo', 'values': values}], update=True)
            foo.invalidate_recordset()
            return bool(written)

        # nothing changes: no write
        self.assertFalse(load({'name': 'foo'}))
        self.assertFalse(load({'name': 'foo', 'bar_ids': []}))
        self.assertFalse(load({'bar_ids': [Command.link(bar.id)]}))
        self.assertFalse(load({'bar_ids': [Command.link(inactive_bar.id)]}))
        self.assertFalse(load({'bar_ids': [Command.unlink(Bar.create({}).id)]}))
        # UNLINK does not remove inactive records from many2many fields
        self.assertFalse(load({'bar_ids': [Command.unlink(inactive_bar.id)]}))
        self.assertEqual(foo.with_context(active_test=False).bar_ids, bar + inactive_bar)

        # something may change: write
        self.assertTrue(load({'name': 'bar'}))
        self.assertEqual(foo.name, 'bar')
        self.assertTrue(load({'bar_ids': [Command.set([bar.id, inactive_bar.id])]}))
        self.assertTrue(load({'bar_ids': [bar.id, inactive_bar.id]}))
        self.assertTrue(load({'bar_ids': [Command.link(bar.id), Command.link(inactive_bar.id)]}))
        self.assertEqual(foo.with_context(active_test=False).bar_ids, bar + inactive_bar)
        # a list of ids is a SET command
        self.assertTrue(load({'bar_ids': [inactive_bar.id]}))
        self.assertEqual(foo.with_context(active_test=False).bar_ids, inactive_bar)

        # CLEAR does not remove inactive records from many2many fields
        self.assertFalse(load({'bar_ids': [Command.clear()]}))
        self.assertEqual(foo.with_context(active_test=False).bar_ids, inactive_bar)

        # UNLINK and CLEAR remove active records
        self.assertTrue(load({'bar_ids': [Command.link(bar.id)]}))
        self.assertTrue(load({'bar_ids': [Command.unlink(bar.id)]}))
        self.assertEqual(foo.with_context(active_test=False).bar_ids, inactive_bar)
        self.assertTrue(load({'bar_ids': [Command.link(bar.id)]}))
        self.assertTrue(load({'bar_ids': [Command.clear()]}))
        self.assertEqual(foo.with_context(active_test=False).bar_ids, inactive_bar)
