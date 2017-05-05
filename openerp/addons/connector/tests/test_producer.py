# -*- coding: utf-8 -*-

import mock

import openerp.tests.common as common
from openerp.addons.connector.event import (
    on_record_create,
    on_record_write,
    on_record_unlink
)


class test_producers(common.TransactionCase):
    """ Test producers """

    def setUp(self):
        super(test_producers, self).setUp()

        class Recipient(object):
            pass

        self.recipient = Recipient()
        self.model = self.env['res.partner']
        self.partner = self.model.create({'name': 'new'})

    def test_on_record_create(self):
        """
        Create a record and check if the event is called
        """
        @on_record_create(model_names='res.partner')
        def event(session, model_name, record_id, vals):
            self.recipient.record_id = record_id

        record = self.model.create({'name': 'Kif Kroker'})
        self.assertEqual(self.recipient.record_id, record.id)
        on_record_create.unsubscribe(event)

    def test_on_record_write(self):
        """
        Write on a record and check if the event is called
        """
        @on_record_write(model_names='res.partner')
        def event(session, model_name, record_id, vals=None):
            self.recipient.record_id = record_id
            self.recipient.vals = vals

        vals = {'name': 'Lrrr',
                'city': 'Omicron Persei 8'}
        self.partner.write(vals)
        self.assertEqual(self.recipient.record_id, self.partner.id)
        self.assertDictEqual(self.recipient.vals, vals)
        on_record_write.unsubscribe(event)

    def test_on_record_unlink(self):
        """
        Unlink a record and check if the event is called
        """
        @on_record_unlink(model_names='res.partner')
        def event(session, model_name, record_id):
            if model_name == 'res.partner':
                self.recipient.record_id = record_id

        self.partner.unlink()
        self.assertEqual(self.recipient.record_id, self.partner.id)
        on_record_write.unsubscribe(event)

    def test_on_record_write_no_consumer(self):
        """
        If no consumer is registered on the event for the model,
        the event should not be fired at all
        """
        # clear all the registered events
        on_record_write._consumers = {None: set()}
        with mock.patch.object(on_record_write, 'fire'):
            self.partner.write({'name': 'Kif Kroker'})
            self.assertEqual(on_record_write.fire.called, False)
