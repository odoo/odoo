/** @odoo-module **/

import LineComponent from '@stock_barcode/components/line';
import { patch } from "@web/core/utils/patch";


patch(LineComponent.prototype, {

    get componentClasses() {
        return [
            super.componentClasses,
            this.line.colorLine !== undefined ? 'o_colored_markup' : ''
        ].join(' ');
    },

    get pickingName() {
        if (this.env.model.resModel === "stock.picking.batch") {
            if (this.line.lines?.length > 1) {
                // Don't display picking name if line has sublines belonging to different pickings.
                const pickingId = this.line.picking_id.id;
                for (const line of this.line.lines) {
                    if (line.picking_id.id != pickingId) {
                        return false;
                    }
                }
            }
            return this.line.picking_id.name;
        }
        return false;
    },
});

LineComponent.props = [...LineComponent.props, "hidePickingName?"];
