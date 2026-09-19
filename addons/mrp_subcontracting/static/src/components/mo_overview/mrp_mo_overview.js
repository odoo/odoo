import { patch } from "@web/core/utils/patch";
import { MoOverview } from "@mrp/components/mo_overview/mrp_mo_overview";

patch(MoOverview.prototype, {
    async getManufacturingData() {
        await super.getManufacturingData();
        this.state.showOptions.subcontractorAvailabilities = this.is_subcontract;
    },

    get is_subcontract() {
        return !!this.state.data.summary.is_subcontract;
    },

    get totalColspan() {
        let totalColspan = super.totalColspan;
        if (this.showAvailabilities && this.is_subcontract) {
            totalColspan++;
        }
        return totalColspan;
    },
});
