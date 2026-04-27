/** @odoo-module **/

import GroupedLineComponent from '@stock_barcode/components/grouped_line';
import { patch } from "@web/core/utils/patch";


patch(GroupedLineComponent.prototype, {
    get sublineProps() {
        const props = super.sublineProps;
        if (this.env.model.resModel === "stock.picking.batch") {
            // Don't display the picking on sublines if already displayed on grouped line.
            props.hidePickingName = Boolean(this.pickingName);
        }
        return props;
    },

    get displayToggleBtn() {
        if (this.env.model.resModel === "stock.picking.batch" && !Boolean(this.pickingName)) {
            return true;
        }
        return super.displayToggleBtn;
    },

    get linesToDisplay() {
        if (this.env.model.resModel === "stock.picking.batch" && !Boolean(this.pickingName)) {
            return this.props.line.lines;
        }
        return super.linesToDisplay;
    },
});
