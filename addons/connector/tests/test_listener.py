# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from unittest import mock

from odoo.tools import frozendict

from odoo.addons.component.core import Component
from odoo.addons.component.tests.common import TransactionComponentRegistryCase
from odoo.addons.component_event.components.event import skip_if
from odoo.addons.component_event.core import EventWorkContext
from odoo.addons.connector import components


class TestEventListener(TransactionComponentRegistryCase):
    """Test Connecter Listener"""

    def setUp(self):
        super().setUp()
        self._setup_registry(self)

    def test_skip_if_no_connector_export(self):
        class MyEventListener(Component):
            _name = "my.event.listener"
            _inherit = "base.event.listener"

            def on_record_create(self, record, fields=None):
                assert True

        class MyOtherEventListener(Component):
            _name = "my.other.event.listener"
            _inherit = "base.connector.listener"

            @skip_if(lambda self, record, fields=None: self.no_connector_export(record))
            def on_record_create(self, record, fields=None):
                raise AssertionError()

        self.env.context = frozendict(self.env.context, no_connector_export=True)
        work = EventWorkContext(
            model_name="res.users", env=self.env, components_registry=self.comp_registry
        )

        # get the collecter to notify the event
        # we don't mind about the collection and the model here,
        # the events we test are global
        self.collecter = self.comp_registry["base.event.collecter"](work)

        self._build_components(
            components.core.BaseConnectorComponent,
            components.listener.ConnectorListener,
            MyEventListener,
            MyOtherEventListener,
        )

        # collect the event and notify it
        record = mock.Mock(name="record")
        collected = self.collecter.collect_events("on_record_create")
        self.assertEqual(2, len(collected.events))
        collected.notify(record)
