import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from '@odoo/owl';
import { SearchPanel } from "@web/search/search_panel/search_panel";


export class StockOrderpointSearchPanel extends SearchPanel {
    static template = "stock.StockOrderpointSearchPanel";

    setup() {
        this.orm = useService("orm");
        super.setup(...arguments);
        this.globalHorizonDays = useState({value: 0});
        onWillStart(this.getHorizonParameter);
    }

    async getHorizonParameter() {
        let res = await this.orm.call("stock.warehouse.orderpoint", "get_horizon_days", [0]);
        this.globalHorizonDays.value = Math.abs(parseInt(res)) || 0;
    }

    async applyGlobalHorizonDays(ev) {
        this.globalHorizonDays.value = Math.max(parseInt(ev.target.value || 0), 0);
        await this.env.searchModel.applyGlobalHorizonDays(this.globalHorizonDays.value);
    }
}
