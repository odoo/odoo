import { useProps, t } from "@odoo/owl";
import {
    MO_OVERVIEW_SUMMARY_SHAPE,
    MoOverviewBaseBlock,
    moOverviewBaseBlockProps,
} from "../mo_overview_operations_block/mrp_mo_overview_operations_block";
import { MoOverviewLine } from "../mo_overview_line/mrp_mo_overview_line";

export class MoOverviewByproductsBlock extends MoOverviewBaseBlock {
    static components = {
        MoOverviewLine,
    };
    props = useProps({
        ...moOverviewBaseBlockProps,
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
