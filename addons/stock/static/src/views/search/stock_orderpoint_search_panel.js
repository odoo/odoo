/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from '@odoo/owl';
import { SearchPanel } from "@web/search/search_panel/search_panel";


export class StockOrderpointSearchPanel extends SearchPanel {
    static template = "stock.StockOrderpointSearchPanel";

    setup() {
        this.orm = useService("orm");
        super.setup(...arguments);
        this.globalVisibilityDays = useState({value: 0});
        this.state.sidebarExpanded = false;
        onWillStart(this.getVisibilityParameter);
    }

    async getVisibilityParameter() {
        let res = await this.orm.call("stock.warehouse.orderpoint", "get_visibility_days", []);
        this.globalVisibilityDays.value = Math.abs(parseInt(res)) || 0;
    }

    async applyGlobalVisibilityDays(ev) {
        this.globalVisibilityDays.value = Math.max(parseInt(ev.target.value), 0);
        await this.env.searchModel.applyGlobalVisibilityDays(this.globalVisibilityDays.value);
    }
}
