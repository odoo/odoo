/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BomOverviewComponent } from "@mrp/components/bom_overview/mrp_bom_overview";

patch(BomOverviewComponent.prototype, {
    setup() {
        super.setup();
        this.state.showOptions.ecos = false;
        this.state.showOptions.ecoAllowed = false;
    },

    async getBomData() {
        const bomData = await super.getBomData();
        this.state.showOptions.ecoAllowed = bomData['is_eco_applied'];
        return bomData;
    },

    getReportName(printAll) {
        return super.getReportName(...arguments) + "&show_ecos=" + (this.state.showOptions.ecoAllowed && this.state.showOptions.ecos);
    }
});
