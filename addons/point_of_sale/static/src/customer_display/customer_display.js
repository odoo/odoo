import { Component, useState, whenReady } from "@odoo/owl";
import { OdooLogo } from "@point_of_sale/app/generic_components/odoo_logo/odoo_logo";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { mountComponent } from "@web/env";

export class CustomerDisplay extends Component {
    static template = "point_of_sale.CustomerDisplay";
    static components = { OdooLogo, OrderWidget, Orderline, MainComponentsContainer };
    static props = [];
    setup() {
        this.session = session;
        this.dialog = useService("dialog");
        this.order = useState(useService("customer_display_data"));
    }
}
whenReady(() => mountComponent(CustomerDisplay, document.body));
