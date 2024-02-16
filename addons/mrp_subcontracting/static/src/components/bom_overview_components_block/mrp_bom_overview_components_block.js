import { patch } from "@web/core/utils/patch";
import { BomOverviewComponentsBlock } from "@mrp/components/bom_overview_components_block/mrp_bom_overview_components_block";
import { BomOverviewSpecialLine } from "@mrp/components/bom_overview_special_line/mrp_bom_overview_special_line";

patch(BomOverviewComponentsBlock, {
    components: { ...BomOverviewComponentsBlock.components, BomOverviewSpecialLine },
});
