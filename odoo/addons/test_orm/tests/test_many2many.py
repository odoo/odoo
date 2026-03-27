from unittest.mock import patch

from odoo.fields import Command, Domain
from odoo.tests.common import TransactionCase, new_test_user


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
            'real_binary': b'aGV5',
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
        record = self.env['test_orm.attachment.host'].create({
            'm2m_attachment_ids': [Command.link(attachment.id)],
        }).with_user(user)

        self.assertFalse(record.env.su)

        field = record._fields['m2m_attachment_ids']
        self.assertTrue(field.bypass_search_access)

        # check that attachments are searched with bypass_access, and filtered with _check_access()
        Attachment = type(attachment)
        with (
            patch.object(Attachment, '_search', autospec=True, side_effect=Attachment._search) as _search,
            patch.object(Attachment, '_check_access', autospec=True, return_value=None) as _check_access,
        ):
            record.invalidate_model()
            record.m2m_attachment_ids
            _search.assert_called_once_with(attachment.browse(), Domain.TRUE, order='id', bypass_access=True)
            _check_access.assert_called_once_with(attachment, 'read')

        # check that otherwise, attachments are searched without bypass_access
        self.patch(field, 'bypass_search_access', False)
        with (
            patch.object(Attachment, '_search', autospec=True, side_effect=Attachment._search) as _search,
            patch.object(Attachment, '_check_access', autospec=True, return_value=None) as _check_access,
        ):
            record.invalidate_model()
            record.m2m_attachment_ids
            _search.assert_called_once_with(attachment.browse(), Domain.TRUE, order='id', bypass_access=False)
            _check_access.assert_called_once_with(attachment.browse(), 'read')
