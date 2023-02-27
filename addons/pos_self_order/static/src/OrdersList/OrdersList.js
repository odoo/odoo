/** @odoo-module */

const { Component, useState, onWillStart } = owl;
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { OrderView } from "../OrderView/OrderView.js";
import { formatMonetary } from "@web/views/fields/formatters";
import { PaymentMethodsSelect } from "@pos_self_order/PaymentMethodsSelect/PaymentMethodsSelect";
import { NavBar } from "@pos_self_order/NavBar/NavBar";

export class OrdersList extends Component {
    setup() {
        this.selfOrder = useSelfOrder();
        this.state = useState(this.env.state);
        this.orders_list = [];
        this.formatMonetary = formatMonetary;
        this.rpc = useService("rpc");
        onWillStart(async () => {
            if (this.selfOrder.config.self_order_location === "table") {
                this.orders_list = await this.updateOrdersFromLocalStorage();
            }
        });
    }
    /**
     * @param {Order} order
     * @returns
     */
    async getUpdatedOrderFromServer(order) {
        try {
            console.log("getting update for order ", order.order_id, order.access_token);
            return await this.rpc(`/pos-self-order/view-order/`, {
                order_id: order.order_id,
                access_token: order.access_token,
            });
        } catch (error) {
            console.error(error);
        }
    }
    /**
     * @param {Order[]} old_orders_list
     * @returns {Order[]}
     */
    async getUpdatedOrdersListFromServer(old_orders_list) {
        return await Promise.all(
            old_orders_list.map(async (order) =>
                order.state === "paid" ? order : await this.getUpdatedOrderFromServer(order)
            )
        );
    }
    // FIXME: it happens that the "orders_list" in local storage = [null]
    // this causes problems
    async updateOrdersFromLocalStorage() {
        const old_orders_list = JSON.parse(localStorage.getItem("orders_list")) ?? [];
        this.orders_list = await this.getUpdatedOrdersListFromServer(old_orders_list);
        localStorage.setItem("orders_list", JSON.stringify(this.orders_list));
        return this.orders_list;
    }
    static components = { OrderView, PaymentMethodsSelect, NavBar };
}
OrdersList.template = "OrdersList";
export default { OrdersList };
