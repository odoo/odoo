/** @odoo-module **/

import { useState } from '@odoo/owl';
import { SearchPanel } from "@web/search/search_panel/search_panel";


export class StockOrderpointSearchPanel extends SearchPanel {
    static template = "stock.StockOrderpointSearchPanel";

    setup() {
        super.setup(...arguments);
        const storedVal = localStorage.getItem("stock.orderpoint_horizon")
        this.globalVisibilityDays = useState({value: storedVal === null ? 0 : parseInt(storedVal)});
    }

    async applyGlobalVisibilityDays(ev) {
        this.globalVisibilityDays.value = Math.max(parseInt(ev.target.value), 0);
        localStorage.setItem("stock.orderpoint_horizon", this.globalVisibilityDays.value.toString());
        await this.env.searchModel.applyGlobalVisibilityDays(this.globalVisibilityDays.value);
    }
}
