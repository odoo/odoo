import { Component, t, useProps } from "@odoo/owl";
import { sortBy } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";

export const groupProps = {
    class: t.any().optional(),
    slots: t.any().optional(),
    maxCols: t.any().optional(2),
    style: t.any().optional(),
};

class Group extends Component {
    static template = "";
    static propShape = groupProps;
    props = useProps(this.constructor.propShape);

    _getItems() {
        const items = Object.entries(this.props.slots || {}).filter(([k, v]) => v.type === "item");
        return sortBy(items, (i) => i[1].sequence);
    }

    getItems() {
        return this._getItems().filter(([, slot]) => !("isVisible" in slot) || slot.isVisible);
    }

    get allClasses() {
        return this.props.class;
    }
}

export class OuterGroup extends Group {
    static template = "web.Form.OuterGroup";
    static propShape = {
        ...groupProps,
        slots: t.any().optional([]),
        hasOuterTemplate: t.any().optional(true),
    };
    props = useProps(this.constructor.propShape);

    getItems() {
        const nbCols = this.props.maxCols;
        const colSize = Math.max(1, Math.round(12 / nbCols));

        // Dispatch items across table rows
        return super.getItems().map((item) => {
            const [slotName, slot] = item;
            const itemSpan = slot.itemSpan || 1;
            return {
                name: slotName,
                size: itemSpan * colSize,
                newline: slot.newline,
                colspan: itemSpan,
            };
        });
    }
}

export class InnerGroup extends Group {
    static template = "web.Form.InnerGroup";
    setup() {
        this.uiService = useService("ui");
    }
    getTemplate(subType) {
        return this.constructor.templates[subType] || this.constructor.templates.default;
    }
    getRows() {
        const maxCols = this.props.maxCols;

        const rows = [];
        let currentRow = [];
        let reservedSpace = 0;

        // Dispatch items across table rows
        for (const [slotName, slot] of this.getItems()) {
            const itemSpan = slot.itemSpan || 1;
            if (slot.newline || itemSpan + reservedSpace > maxCols) {
                rows.push(currentRow);
                currentRow = [];
                reservedSpace = 0;
            }

            currentRow.push({ ...slot, name: slotName });
            reservedSpace += itemSpan;
        }
        rows.push(currentRow);

        // Remove the rows that ended up empty (e.g. a "newline" before the first visible item).
        return rows.filter((row) => row.length);
    }
}
