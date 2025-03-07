import { Component, whenReady } from "@odoo/owl";
import { OdooLogo } from "@point_of_sale/app/components/odoo_logo/odoo_logo";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { mountComponent } from "@web/env";

export class CustomerDisplay extends Component {
    static template = "point_of_sale.CustomerDisplay";
    static components = { OdooLogo, MainComponentsContainer };
    static props = [];
    setup() {
        this.session = session;
        this.dialog = useService("dialog");
        this.order = useService("customer_display_data");
    }
}
whenReady(() => mountComponent(CustomerDisplay, document.body));
