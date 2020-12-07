/** @odoo-module alias=point_of_sale.OrderManagementScreen **/

import AbstractOrderManagementScreen from 'point_of_sale.AbstractOrderManagementScreen';
import OrderDetails from 'point_of_sale.OrderDetails';
import OrderManagementControlPanel from 'point_of_sale.OrderManagementControlPanel';
import OrderList from 'point_of_sale.OrderList';
import InvoiceButton from 'point_of_sale.InvoiceButton';
import ReprintReceiptButton from 'point_of_sale.ReprintReceiptButton';
import ActionpadWidget from 'point_of_sale.ActionpadWidget';
import NumpadWidget from 'point_of_sale.NumpadWidget';
import MobileOrderManagementScreen from 'point_of_sale.MobileOrderManagementScreen';

class OrderManagementScreen extends AbstractOrderManagementScreen {
    willUnmount() {
        // We are doing this so that the next time this screen is rendered
        // ordersToShow won't contain deleted activeOrders.
        this.env.model.orderFetcher.ordersToShow = [];
    }
}
OrderManagementScreen.components = {
    OrderDetails,
    OrderManagementControlPanel,
    OrderList,
    InvoiceButton,
    ReprintReceiptButton,
    ActionpadWidget,
    NumpadWidget,
    MobileOrderManagementScreen,
};
OrderManagementScreen.template = 'point_of_sale.OrderManagementScreen';

export default OrderManagementScreen;
