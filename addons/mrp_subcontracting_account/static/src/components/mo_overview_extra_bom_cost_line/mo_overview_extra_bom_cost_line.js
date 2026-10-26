import {
    MoOverviewComponentsBlock
} from "@mrp/components/mo_overview_components_block/mrp_mo_overview_components_block";
import {patch} from "@web/core/utils/patch";


patch(MoOverviewComponentsBlock.prototype, {
    setup() {
        super.setup();
        if (this.props.summary.is_subcontract) {
            this.extraCostTitle = "Subcontracting Cost";
        }
    },
});
