/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BomOverviewSpecialLine } from "@mrp/components/bom_overview_special_line/mrp_bom_overview_special_line";

patch(BomOverviewSpecialLine, {
    props: {
        ...BomOverviewSpecialLine.props,
        showOptions: { 
            ...BomOverviewSpecialLine.showOptions,
            ecos: Boolean,
            ecoAllowed: Boolean,
        },
    },
});
