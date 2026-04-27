/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";

import { useEffect, useRef } from "@odoo/owl";

patch(PivotRenderer.prototype, {
    setup() {
        super.setup();
        this.root = useRef("root");
        if (this.env.isSmall) {
            useEffect(() => {
                if (this.root.el) {
                    const tooltipElems = this.root.el.querySelectorAll("*[data-tooltip]");
                    for (const el of tooltipElems) {
                        el.removeAttribute("data-tooltip");
                        el.removeAttribute("data-tooltip-position");
                    }
                }
            });
        }
    },

    getPadding(cell) {
        if (this.env.isSmall) {
            return 5 + cell.indent * 5;
        }
        return super.getPadding(...arguments);
    },
});
