/** @odoo-module **/

import { useState } from '@odoo/owl';
import { SearchPanel } from "@web/search/search_panel/search_panel";


export class StockOrderpointSearchPanel extends SearchPanel {
    static template = "stock.StockOrderpointSearchPanel";

    setup() {
        super.setup(...arguments);
        this.globalVisibilityDays = useState({value: 0});
        this.state.sidebarExpanded = false;
    }

    async applyGlobalVisibilityDays(ev) {
        this.globalVisibilityDays.value = Math.max(parseInt(ev.target.value), 0);
        await this.env.searchModel.applyGlobalVisibilityDays(this.globalVisibilityDays.value);
    }
}
