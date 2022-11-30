/** @odoo-module alias=pos_event.ProductScreen */

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { identifyError } from 'point_of_sale.utils';
import { ConnectionLostError, ConnectionAbortedError } from '@web/core/network/rpc_service';
import { useListener } from '@web/core/utils/hooks';




export class EventButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClick);
    }
    async onClick() {
        try {
            const eventData = await this.rpc({
                model: 'event.event.ticket',
                method: 'get_ticket_linked_to_product_available_pos',
            });
            const { confirmed, payload } = await this.showPopup('EventConfiguratorPopup', { eventData });
            if (confirmed) {
                const { eventName, ticketDetails } = payload;
                const currentOrder = this.env.pos.get_order();
                for (const ticketDetail of ticketDetails) {
                    const product = this.env.pos.db.get_product_by_id(ticketDetail.productId);
                    const options = { quantity: ticketDetail.quantity, description: `[${eventName}]`, ticketId: ticketDetail.ticketId};
                    currentOrder.add_product(product, options);
                }
            }
        } catch (e) {
            const error = identifyError(e);
            if (error instanceof ConnectionLostError || error instanceof ConnectionAbortedError) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Network Error'),
                    body: this.env._t('Cannot load Events and Tickets'),
                });
            } else {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Unknown error'),
                    body: this.env._t('Cannot load Events and Tickets due to an unknown error.'),
                });
            }
        }
    }
}
EventButton.template = 'EventButton';

ProductScreen.addControlButton({
    component: EventButton,
});

Registries.Component.add(EventButton);
