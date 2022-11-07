/** @odoo-module */
import { sortBy } from "@web/core/utils/arrays";

class Group extends owl.Component {
    _getItems() {
        const items = Object.entries(this.props.slots || {}).filter(([k, v]) => v.type === "item");
        return sortBy(items, (i) => i[1].sequence);
    }

    getItems() {
        return this._getItems();
    }

    get allClasses() {
        return this.props.class;
    }
}
Group.props = ["class?", "slots?", "maxCols?", "style?"];
Group.defaultProps = {
    maxCols: 2,
};

export class OuterGroup extends Group {
    getItems() {
        const nbCols = this.props.maxCols;
        const colSize = Math.max(1, Math.round(12 / nbCols));

        // Dispatch items across table rows
        const items = super.getItems().filter(([k, v]) => !("isVisible" in v) || v.isVisible);
        return items.map((item) => {
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
OuterGroup.template = "web.Form.OuterGroup";
OuterGroup.defaultProps = {
    ...Group.defaultProps,
    slots: [],
    hasOuterTemplate: true,
};

export class InnerGroup extends Group {
    getTemplate(subType) {
        return this.constructor.templates[subType] || this.constructor.templates.default;
    }
    getRows() {
        const maxCols = this.props.maxCols;

        const rows = [];
        let currentRow = [];
        let reservedSpace = 0;

        // Dispatch items across table rows
        const items = this.getItems();
        while (items.length) {
            const [slotName, slot] = items.shift();
            const { newline, itemSpan } = slot;
            if (newline) {
                rows.push(currentRow);
                currentRow = [];
                reservedSpace = 0;
            }

            const fullItemSpan = itemSpan || 1;

            if (fullItemSpan + reservedSpace > maxCols) {
                rows.push(currentRow);
                currentRow = [];
                reservedSpace = 0;
            }

            const isVisible = !("isVisible" in slot) || slot.isVisible;
            currentRow.push({ ...slot, name: slotName, itemSpan, isVisible });
            reservedSpace += itemSpan || 1;

            // Allows to remove the line if the content is not visible instead of leaving an empty line.
            currentRow.isVisible = currentRow.isVisible || isVisible;
        }
        rows.push(currentRow);
        return rows;
    }
}
InnerGroup.template = "web.Form.InnerGroup";
