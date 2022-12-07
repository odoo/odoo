/** @odoo-module **/

import TicketScreen from 'point_of_sale.TicketScreen';
import Registries from 'point_of_sale.Registries';


export const PosFrTicketScreen = (TicketScreen) =>
    class PosFrTicketScreen extends TicketScreen {
        shouldHideDeleteButton(order) {
            return this.env.pos.is_french_country() || super.shouldHideDeleteButton(order);
        }
    };

Registries.Component.extend(TicketScreen, PosFrTicketScreen);
