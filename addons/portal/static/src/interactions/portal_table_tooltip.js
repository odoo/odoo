import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class PortalTableTooltip extends Interaction {
    static selector = ".o_portal_my_doc_table";
    dynamicContent = {
        "td, th": { "t-on-mouseenter": this.updateTooltip },
    };

    setup() {
        this.tooltipCellEls = new Set();
        this.registerCleanup(() => {
            for (const cellEl of this.tooltipCellEls) {
                delete cellEl.dataset.tooltip;
            }
        });
    }

    /**
     * @param {MouseEvent} ev
     */
    updateTooltip(ev) {
        const cellEl = ev.currentTarget;
        // Keep any tooltip or title coming from the template as is.
        if (
            (cellEl.dataset.tooltip !== undefined && !this.tooltipCellEls.has(cellEl)) ||
            cellEl.hasAttribute("title")
        ) {
            return;
        }
        const text = cellEl.textContent.replace(/\s+/g, " ").trim();
        if (text && cellEl.offsetWidth < cellEl.scrollWidth) {
            cellEl.dataset.tooltip = text;
            this.tooltipCellEls.add(cellEl);
        } else {
            delete cellEl.dataset.tooltip;
            this.tooltipCellEls.delete(cellEl);
        }
    }
}

registry.category("public.interactions").add("portal.portal_table_tooltip", PortalTableTooltip);
