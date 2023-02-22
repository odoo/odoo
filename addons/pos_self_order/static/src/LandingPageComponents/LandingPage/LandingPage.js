/** @odoo-module */

const { Component, useState, onWillStart } = owl;
import { LandingPageHeader } from "../LandingPageHeader/LandingPageHeader.js";
import { LandingPageFooter } from "../LandingPageFooter/LandingPageFooter.js";
import { AlertMessage } from "../../AlertMessage/AlertMessage.js";
import { OrdersList } from "../../OrdersList/OrdersList.js";
import { PaymentMethodsSelect } from "../../PaymentMethodsSelect/PaymentMethodsSelect.js";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
export class LandingPage extends Component {
    setup() {
        this.state = useState(this.env.state);
        this.orders_list = [];
        this.selfOrder = useSelfOrder();
        onWillStart(async () => {
            if (this.selfOrder.config.self_order_location === "table") {
                this.orders_list = await this.updateOrdersFromLocalStorage();
            }
        });
        this.user_has_provided_name = this.state.user_name == "" ? false : true;
        // this.Number.isInteger = Number.isInteger;
    }
    resetNameAndTableNumber() {
        this.state.user_name = "";
        this.state.table_id = "";
        this.user_has_provided_name = false;
    }
    async updateOrdersFromLocalStorage() {
        const old_orders_list = JSON.parse(localStorage.getItem("orders_list")) ?? [];
        this.orders_list = await this.props.getUpdatedOrdersListFromServer(old_orders_list);
        localStorage.setItem("orders_list", JSON.stringify(this.orders_list));
        return this.orders_list;
    }

    static components = {
        LandingPageHeader,
        LandingPageFooter,
        OrdersList,
        PaymentMethodsSelect,
        AlertMessage,
    };
}
LandingPage.template = "LandingPage";
export default { LandingPage };
