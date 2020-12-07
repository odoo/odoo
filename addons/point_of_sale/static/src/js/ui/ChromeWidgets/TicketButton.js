/** @odoo-module alias=point_of_sale.TicketButton **/

import PosComponent from 'point_of_sale.PosComponent';

class TicketButton extends PosComponent {
    getNumberOfOrders() {
        return this.env.model.getDraftOrders().length;
    }
}
TicketButton.template = 'point_of_sale.TicketButton';

export default TicketButton;
