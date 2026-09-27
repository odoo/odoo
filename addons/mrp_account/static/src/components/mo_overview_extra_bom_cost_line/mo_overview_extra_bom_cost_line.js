import {formatFloat, formatMonetary} from "@web/views/fields/formatters";
import {
    MoOverviewComponentsBlock
} from "@mrp/components/mo_overview_components_block/mrp_mo_overview_components_block";
import {patch} from "@web/core/utils/patch";


patch(MoOverviewComponentsBlock.prototype, {
    setup() {
        super.setup();
        this.formatMonetary = (val) => formatMonetary(val, {currencyId: this.props.summary.currency_id});
        this.formatFloat = formatFloat;
    },
});