import { onWillStart, proxy, usePlugin } from '@odoo/owl';
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { ORM } from "@web/core/orm_plugin";


export class StockOrderpointSearchPanel extends SearchPanel {
    static template = "stock.StockOrderpointSearchPanel";

    setup() {
        this.orm = usePlugin(ORM);
        super.setup(...arguments);
        this.globalHorizonDays = proxy({value: 0});
        onWillStart(this.getHorizonParameter);
    }

    async getHorizonParameter() {
        let res = await this.orm.call("res.company", "get_horizon_days", [0]);
        this.globalHorizonDays.value = Math.abs(parseInt(res)) || 0;
    }

    async applyGlobalHorizonDays(ev) {
        this.globalHorizonDays.value = Math.max(parseInt(ev.target.value || 0), 0);
        await this.env.searchModel.applyGlobalHorizonDays(this.globalHorizonDays.value);
    }
}
