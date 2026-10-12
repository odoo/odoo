import {formatFloat, formatMonetary} from "@web/views/fields/formatters";
import {patch} from "@web/core/utils/patch";
import {
    BomOverviewComponentsBlock
} from "@mrp/components/bom_overview_components_block/mrp_bom_overview_components_block";


patch(BomOverviewComponentsBlock.prototype, {
    setup() {
        super.setup();
        this.formatMonetary = (val) => formatMonetary(val, {currencyId: this.props.data.currency_id});
        this.formatFloat = formatFloat;
    },
});