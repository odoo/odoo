/** @odoo-module alias=point_of_sale.OrderList **/

import PosComponent from 'point_of_sale.PosComponent';

/**
 * @props {'pos.order'[]} orders
 */
class OrderList extends PosComponent {
    isHighlighted(order) {
        return order.id === this.env.model.data.uiState.OrderManagementScreen.activeOrderId;
    }
    getFormattedDate(date) {
        return moment(date).format('YYYY-MM-DD hh:mm A');
    }
}
OrderList.template = 'point_of_sale.OrderList';

export default OrderList;
