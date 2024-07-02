/** @odoo-module **/

import { useService } from '@web/core/utils/hooks';
import { SearchPanel } from "@web/search/search_panel/search_panel";


export class StockOrderpointSearchPanel extends SearchPanel {
    static template = "stock.StockOrderpointSearchPanel";

    setup() {
        super.setup(...arguments);
        this.orm = useService('orm');
    }

    async applyGlobalVisibilityDays(ev) {
        const globalVisibilityDays = parseInt(ev.target.value);
        this.env.searchModel.applyGlobalVisibilityDays(globalVisibilityDays);
    }
}
