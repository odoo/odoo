import { registry } from "@web/core/registry";
import { Many2ManyCheckboxesField, many2ManyCheckboxesField } from "@web/views/fields/many2many_checkboxes/many2many_checkboxes_field";
import { useState } from "@odoo/owl";

export class StockMany2ManyCheckboxesField extends Many2ManyCheckboxesField {
    setup() {
        super.setup();
        this.state = useState({ allowedRouteIds: new Set() });
        this.loadRoutes();
    }

    async loadRoutes() {
        const routes = await this.env.model.orm.searchRead(
            "stock.route",
            [["product_selectable", "=", true]],
            ["id"]
        );
        this.state.allowedRouteIds = new Set(routes.map(route => route.id));
    }

    get items() {
        return this.specialData.data.filter(item => this.state.allowedRouteIds.has(item[0]));
    }

}

registry.category("fields").add("stock_many2many_checkboxes", {
    ...many2ManyCheckboxesField,
    component: StockMany2ManyCheckboxesField,
});
