import { Component, whenReady } from "@odoo/owl";
import { OdooLogo } from "@point_of_sale/app/components/odoo_logo/odoo_logo";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { mountComponent } from "@web/env";
import { TagsList } from "@web/core/tags_list/tags_list";

export class CustomerDisplay extends Component {
    static template = "point_of_sale.CustomerDisplay";
    static components = { OdooLogo, MainComponentsContainer, TagsList };
    static props = [];
    setup() {
        this.session = session;
        this.dialog = useService("dialog");
        this.order = useService("customer_display_data");
    }

    getInternalNotes() {
        return JSON.parse(this.line.internalNote || "[]");
    }
}
whenReady(() => mountComponent(CustomerDisplay, document.body));
