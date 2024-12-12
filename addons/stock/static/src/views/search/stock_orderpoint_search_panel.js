import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from '@odoo/owl';
import { SearchPanel } from "@web/search/search_panel/search_panel";


export class StockOrderpointSearchPanel extends SearchPanel {
    static template = "stock.StockOrderpointSearchPanel";

    setup() {
        this.orm = useService("orm");
        super.setup(...arguments);
        this.state.sidebarExpanded = false;
        this.globalVisibilityDays = useState({value: 0});
        onWillStart(this.getVisibilityParameter);
    }

    async getVisibilityParameter() {
        this.globalVisibilityDays.value = await this.orm.call("ir.config_parameter", "get_param", ["stock.visibility_days", 0]);
    }

    async applyGlobalVisibilityDays(ev) {
        this.globalVisibilityDays.value = Math.max(parseInt(ev.target.value), 0);
        await this.env.searchModel.applyGlobalVisibilityDays(this.globalVisibilityDays.value);
    }
}
