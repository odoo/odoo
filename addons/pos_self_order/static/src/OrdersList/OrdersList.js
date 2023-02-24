/** @odoo-module */

const { Component, useState, onWillStart } = owl;
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { OrderView } from "../OrderView/OrderView.js";
import { formatMonetary } from "@web/views/fields/formatters";
import { PaymentMethodsSelect } from "@pos_self_order/PaymentMethodsSelect/PaymentMethodsSelect.js";
export class OrdersList extends Component {
    setup() {
        this.selfOrder = useSelfOrder();
        this.state = useState(this.env.state);
        this.orders_list = [];
        this.formatMonetary = formatMonetary;
        onWillStart(async () => {
            if (this.selfOrder.config.self_order_location === "table") {
                this.orders_list = await this.updateOrdersFromLocalStorage();
            }
        });
    }
    async updateOrdersFromLocalStorage() {
        const old_orders_list = JSON.parse(localStorage.getItem("orders_list")) ?? [];
        this.orders_list = await this.props.getUpdatedOrdersListFromServer(old_orders_list);
        localStorage.setItem("orders_list", JSON.stringify(this.orders_list));
        return this.orders_list;
    }
    static components = { OrderView, PaymentMethodsSelect };
}
OrdersList.template = "OrdersList";
export default { OrdersList };
