/** @odoo-module **/

import { MoOverviewOperationsBlock } from "../mo_overview_operations_block/mrp_mo_overview_operations_block";
import { MoOverviewLine } from "../mo_overview_line/mrp_mo_overview_line";

export class MoOverviewByproductsBlock extends MoOverviewOperationsBlock {
    static template = "mrp.MoOverviewByproductsBlock";

    //---- Getters ----

    get hasByproducts() {
        return this.props?.byproducts?.length > 0;
    }

    get level() {
        return this.hasByproducts ? this.props.byproducts[0].level - 1 : 0;
    }
}

MoOverviewByproductsBlock.components = {
    MoOverviewLine,
};
MoOverviewByproductsBlock.props = {
    // Keep all props except "operations"
    ...(({ operations, ...props}) => props)(MoOverviewOperationsBlock.props),
    byproducts: Array,
};
MoOverviewByproductsBlock.props.summary.shape = {
    ...MoOverviewByproductsBlock.props.summary.shape,
    product_cost: { type: Number, optional: true },
};
