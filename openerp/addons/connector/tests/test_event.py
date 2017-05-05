# -*- coding: utf-8 -*-

import mock

import openerp.tests.common as common
from openerp.addons.connector.event import Event
from openerp.addons.connector.session import ConnectorSession


class test_event(common.TransactionCase):
    """ Test Event """

    def setUp(self):
        super(test_event, self).setUp()
        self.consumer1 = lambda session, model_name: None
        self.consumer2 = lambda session, model_name: None
        self.event = Event()
        self.session = ConnectorSession(self.cr,
                                        self.uid)

    def test_subscribe(self):
        self.event.subscribe(self.consumer1)
        self.assertIn(self.consumer1, self.event._consumers[None])

    def test_subscribe_decorator(self):
        @self.event
        def consumer():
            pass
        self.assertIn(consumer, self.event._consumers[None])

    def test_subscribe_model(self):
        self.event.subscribe(self.consumer1, model_names=['res.users'])
        self.assertIn(self.consumer1, self.event._consumers['res.users'])

    def test_subscribe_decorator_model(self):
        @self.event(model_names=['res.users'])
        def consumer():
            pass
        self.assertIn(consumer, self.event._consumers['res.users'])

    def test_unsubscribe(self):
        self.event.subscribe(self.consumer1)
        self.event.unsubscribe(self.consumer1)
        self.assertNotIn(self.consumer1, self.event._consumers[None])

    def test_unsubscribe_model(self):
        self.event.subscribe(self.consumer1, model_names=['res.users'])
        self.event.unsubscribe(self.consumer1, model_names=['res.users'])
        self.assertNotIn(self.consumer1, self.event._consumers['res.users'])

    def test_unsubscribe_not_existing(self):
        """ Discard without error """
        self.event.unsubscribe(self.consumer1)

    def test_unsubscribe_not_existing_model(self):
        """ Discard without error """
        self.event.unsubscribe(self.consumer1, model_names=['res.users'])

    def test_replacing(self):
        self.event.subscribe(self.consumer1)
        self.event.subscribe(self.consumer2, replacing=self.consumer1)
        self.assertNotIn(self.consumer1, self.event._consumers[None])
        self.assertIn(self.consumer2, self.event._consumers[None])

    def test_replacing_decorator(self):
        @self.event
        def consumer1(session, model_name):
            pass

        @self.event(replacing=consumer1)
        def consumer2(session, model_name):
            pass
        self.assertNotIn(consumer1, self.event._consumers[None])
        self.assertIn(consumer2, self.event._consumers[None])

    def test_replacing_model(self):
        self.event.subscribe(self.consumer1, model_names=['res.users'])
        self.event.subscribe(self.consumer2, replacing=self.consumer1,
                             model_names=['res.users'])
        self.assertNotIn(self.consumer1, self.event._consumers['res.users'])
        self.assertIn(self.consumer2, self.event._consumers['res.users'])

    def test_fire(self):
        """ Fire a consumer """
        class Recipient(object):
            def __init__(self):
                self.message = None

            def set_message(self, message):
                self.message = message

        @self.event
        def set_message(session, model_name, recipient, message):
            recipient.set_message(message)
        recipient = Recipient()
        # an event is fired on a model name
        session = mock.Mock()
        self.event.fire(session, 'res.users', recipient, 'success')
        self.assertEquals(recipient.message, 'success')

    def test_fire_several_consumers(self):
        """ Fire several consumers """
        class Recipient(object):
            def __init__(self):
                self.message = None

            def set_message(self, message):
                self.message = message

        recipient = Recipient()
        recipient2 = Recipient()

        @self.event
        def set_message(session, model_name, message):
            recipient.set_message(message)

        @self.event
        def set_message2(session, model_name, message):
            recipient2.set_message(message)

        # an event is fired on a model name
        session = mock.Mock()
        self.event.fire(session, 'res.users', 'success')
        self.assertEquals(recipient.message, 'success')
        self.assertEquals(recipient2.message, 'success')

    def test_has_consumer_for(self):
        @self.event(model_names=['product.product'])
        def consumer1(session, model_name):
            pass
        self.assertTrue(self.event.has_consumer_for(self.session,
                                                    'product.product'))
        self.assertFalse(self.event.has_consumer_for(self.session,
                                                     'res.partner'))

    def test_has_consumer_for_global(self):
        @self.event
        def consumer1(session, model_name):
            pass
        self.assertTrue(self.event.has_consumer_for(self.session,
                                                    'product.product'))
        self.assertTrue(self.event.has_consumer_for(self.session,
                                                    'res.partner'))

    def test_consumer_uninstalled_module(self):
        """A consumer in a uninstalled module should not be fired"""
        @self.event
        def consumer1(session, model_name):
            pass
        # devious way to test it: the __module__ of a mock is 'mock'
        # and we use __module__ to know the module of the event
        # so, here func is considered to be in a uninstalled module
        func = mock.Mock()
        func.side_effect = Exception('Should not be called')
        self.event(func)
        self.event.fire(self.session, 'res.users')
