import { props, t } from "@odoo/owl";
import {
    MO_OVERVIEW_SUMMARY_SHAPE,
    MoOverviewOperationsBlock,
    moOverviewOperationsBlockProps,
} from "../mo_overview_operations_block/mrp_mo_overview_operations_block";
import { MoOverviewLine } from "../mo_overview_line/mrp_mo_overview_line";

export class MoOverviewByproductsBlock extends MoOverviewOperationsBlock {
    static components = {
        MoOverviewLine,
    };
    props = props({
        // Keep all props except "operations"
        ...(({ operations, ...rest }) => rest)(moOverviewOperationsBlockProps),
        byproducts: t.array(),
        summary: t.object({
            ...MO_OVERVIEW_SUMMARY_SHAPE,
            product_cost: t.number().optional(),
        }),
    });

    static template = "mrp.MoOverviewByproductsBlock";

    //---- Getters ----

    get hasByproducts() {
        return this.props?.byproducts?.length > 0;
    }

    get level() {
        return this.hasByproducts ? this.props.byproducts[0].level - 1 : 0;
    }
}
