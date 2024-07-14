/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BomOverviewTable } from "@mrp/components/bom_overview_table/mrp_bom_overview_table";

patch(BomOverviewTable.prototype, {
    //---- Getters ----

    get showEcos() {
        return this.props.showOptions.ecos;
    }
});

patch(BomOverviewTable, {
    props: {
        ...BomOverviewTable.props,
        showOptions: { 
            ...BomOverviewTable.showOptions,
            ecos: Boolean,
            ecoAllowed: Boolean,
        },
    },
});
