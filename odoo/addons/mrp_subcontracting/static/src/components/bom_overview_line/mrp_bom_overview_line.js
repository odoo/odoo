/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BomOverviewLine } from "@mrp/components/bom_overview_line/mrp_bom_overview_line";

patch(BomOverviewLine.prototype, {
    /**
     * @override
     */
    async goToRoute(routeType) {
        if (routeType == "subcontract") {
            return this.goToAction(this.data.link_id, this.data.link_model);
        }
        return super.goToRoute(...arguments);
    }
});
