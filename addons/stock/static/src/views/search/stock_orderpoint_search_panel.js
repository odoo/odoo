<<<<<<< saas-18.1
||||||| 2efab4e7b90d36ce60c9858576922b504509993a
/** @odoo-module **/

import { useState } from '@odoo/owl';
=======
/** @odoo-module **/

>>>>>>> 7e9f179bf7ea33764b87b33ef12d148db3c5a163
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from '@odoo/owl';
import { SearchPanel } from "@web/search/search_panel/search_panel";


export class StockOrderpointSearchPanel extends SearchPanel {
    static template = "stock.StockOrderpointSearchPanel";

    setup() {
        this.orm = useService("orm");
        super.setup(...arguments);
        this.state.sidebarExpanded = false;
<<<<<<< saas-18.1
        this.globalVisibilityDays = useState({value: 0});
        onWillStart(this.getVisibilityParameter);
    }

    async getVisibilityParameter() {
        this.globalVisibilityDays.value = await this.orm.call("ir.config_parameter", "get_param", ["stock.visibility_days", 0]);
||||||| 2efab4e7b90d36ce60c9858576922b504509993a
=======
        onWillStart(this.getVisibilityParameter);
    }

    async getVisibilityParameter() {
        let res = await this.orm.call("ir.config_parameter", "get_param", ["stock.visibility_days", 0]);
        this.globalVisibilityDays.value = Math.abs(parseInt(res)) || 0;
>>>>>>> 7e9f179bf7ea33764b87b33ef12d148db3c5a163
    }

    async applyGlobalVisibilityDays(ev) {
        this.globalVisibilityDays.value = Math.max(parseInt(ev.target.value), 0);
        await this.env.searchModel.applyGlobalVisibilityDays(this.globalVisibilityDays.value);
    }
}
