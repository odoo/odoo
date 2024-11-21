import { Component } from "@odoo/owl";
import { sortBy } from "@web/core/utils/arrays";

class Group extends Component {
    static template = "";
    static props = ["class?", "slots?", "maxCols?", "style?"];
    static defaultProps = {
        maxCols: 2,
    };

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

export class OuterGroup extends Group {
    static template = "web.Form.OuterGroup";
    static defaultProps = {
        ...Group.defaultProps,
        slots: [],
        hasOuterTemplate: true,
    };

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

export class InnerGroup extends Group {
    static template = "web.Form.InnerGroup";
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
            if (!slot.isVisible) {
                continue;
            }

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
