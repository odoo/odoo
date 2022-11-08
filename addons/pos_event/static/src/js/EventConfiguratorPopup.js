/** @odoo-module alias=pos_event.EventConfiguratorPopup */

import Registries from 'point_of_sale.Registries';
import AbstractAwaitablePopup from 'point_of_sale.AbstractAwaitablePopup';

export class EventConfiguratorPopup extends AbstractAwaitablePopup  {

};

EventConfiguratorPopup.template = 'EventConfiguratorPopup';
Registries.Component.add(EventConfiguratorPopup);
