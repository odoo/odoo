/** @odoo-module alias=point_of_sale.MobileOrderManagementScreen **/

import AbstractOrderManagementScreen from 'point_of_sale.AbstractOrderManagementScreen';
import OrderDetails from 'point_of_sale.OrderDetails';
import OrderManagementControlPanel from 'point_of_sale.OrderManagementControlPanel';
import OrderList from 'point_of_sale.OrderList';
import InvoiceButton from 'point_of_sale.InvoiceButton';
import ReprintReceiptButton from 'point_of_sale.ReprintReceiptButton';
import ActionpadWidget from 'point_of_sale.ActionpadWidget';
import NumpadWidget from 'point_of_sale.NumpadWidget';
const { useState } = owl.hooks;

class MobileOrderManagementScreen extends AbstractOrderManagementScreen {
    constructor() {
        super(...arguments);
        this.mobileState = useState({ showDetails: false });
    }
    async _onClickOrder() {
        this.mobileState.showDetails = true;
        await super._onClickOrder(...arguments);
    }
}
MobileOrderManagementScreen.components = {
    OrderDetails,
    OrderManagementControlPanel,
    OrderList,
    InvoiceButton,
    ReprintReceiptButton,
    ActionpadWidget,
    NumpadWidget,
};
MobileOrderManagementScreen.template = 'point_of_sale.MobileOrderManagementScreen';

export default MobileOrderManagementScreen;
