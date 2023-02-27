/** @odoo-module */

const { Component, useState } = owl;
import { LandingPageHeader } from "../LandingPageHeader/LandingPageHeader.js";
import { LandingPageFooter } from "../LandingPageFooter/LandingPageFooter.js";
import { AlertMessage } from "../../AlertMessage/AlertMessage.js";
import { OrdersList } from "../../OrdersList/OrdersList.js";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { formatMonetary } from "@web/views/fields/formatters";
export class LandingPage extends Component {
    setup() {
        this.state = useState(this.env.state);
        this.selfOrder = useSelfOrder();
        this.formatMonetary = formatMonetary;
        this.user_has_provided_name = this.state.user_name == "" ? false : true;
    }
    resetNameAndTableNumber() {
        this.state.user_name = "";
        this.state.table_id = "";
        this.user_has_provided_name = false;
    }

    static components = {
        LandingPageHeader,
        LandingPageFooter,
        OrdersList,
        AlertMessage,
    };
}
LandingPage.template = "LandingPage";
export default { LandingPage };
