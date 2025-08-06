import { Component, useState, useExternalListener, useRef, onWillRender } from "@odoo/owl";

export const TABLE_TYPES = {
    Id: "id",
    Code: "code-like",
    Tooltip: "tooltip",
};

export class DocTable extends Component {
    static components = { DocTable };
    static template = "web.DocTable";

    static props = {
        data: true,
    };

    setup() {
        this.subTableRef = useRef("subTableRef");
        this.tooltipRef = useRef("tooltipRef");
        this.hideTooltipTimeout = null;
        this.state = useState({
            sortBy: 0,
            sortOrder: "desc",
            subTable: undefined,
            tooltipContent: "",
            tooltipStyle: "",
            lastTooltipLeft: 0,
            lastTooltipTop: 0,
        });

        onWillRender(() => {
            this.items = this.computeItems();
        });

        useExternalListener(window, "click", (event) => {
            if (
                this.subTableRef.el &&
                this.subTableRef.el !== event.target &&
                !this.subTableRef.el.contains(event.target)
            ) {
                this.state.subTable = null;
            }
        });

        useExternalListener(window, "scroll", () => (this.state.subTable = null));
    }

    showDynamicTooltip(event, content) {
        if (this.hideTooltipTimeout) {
            clearTimeout(this.hideTooltipTimeout);
            this.hideTooltipTimeout = null;
        }
        this.state.tooltipContent = content;
        const triggerRect = event.target.getBoundingClientRect();
        this.state.tooltipStyle = `
            opacity: 0;
            pointer-events: none;
        `;
        requestAnimationFrame(() => {
            if (!this.tooltipRef.el) {
                return;
            }
            const tooltipRect = this.tooltipRef.el.getBoundingClientRect();
            const top = triggerRect.top - tooltipRect.height - 10;
            const left = triggerRect.left - tooltipRect.width / 2;
            this.state.tooltipStyle = `
                top: ${top}px;
                left: ${left}px;
                position: fixed;
                opacity: 1;
                pointer-events: auto;
            `;
            this.state.lastTooltipTop = top;
            this.state.lastTooltipLeft = left;
        });
    }

    hideDynamicTooltip() {
        if (this.hideTooltipTimeout) {
            clearTimeout(this.hideTooltipTimeout);
            this.hideTooltipTimeout = null;
        }
        const top = this.state.lastTooltipTop;
        const left = this.state.lastTooltipLeft;
        this.state.tooltipStyle = `
            top: ${top}px;
            left: ${left}px;
            position: fixed;
            opacity: 0;
            pointer-events: none;
        `;
        this.hideTooltipTimeout = setTimeout(() => {
            this.state.tooltipContent = "";
        }, 200);
    }

    computeItems() {
        if (this.state.sortBy >= 0) {
            const items = [...this.props.data.items];
            items.sort((itemA, itemB) => {
                const a = this.getValue(itemA[this.state.sortBy]);
                const b = this.getValue(itemB[this.state.sortBy]);
                if (this.state.sortOrder === "asc") {
                    return b.localeCompare(a);
                } else {
                    return a.localeCompare(b);
                }
            });
            return items;
        } else {
            return this.props.data.items;
        }
    }

    showSubTable(event, subData) {
        if (subData) {
            this.state.subTable = subData;
            const rect = event.target.getBoundingClientRect();
            this.state.subTableStyle = `top: ${rect.bottom + 3}px; left: ${
                rect.left
            }px; z-index: 50;`;
        }
    }

    getId(values) {
        return values.find((v) => v.type === TABLE_TYPES.Id)?.value;
    }

    getTag(row) {
        return row && typeof row === "object" && row.type === "code" ? "pre" : "span";
    }

    getValue(row) {
        return String(row && typeof row === "object" ? row.value : row);
    }

    getClass(row) {
        const classList = [];
        if (row && typeof row === "object") {
            if (row.type === "code") {
                classList.push("font-monospace");
            }
            if (row.class) {
                classList.push(row.class);
            }
        }
        return classList.join(" ");
    }

    onRowHeaderClick(rowIndex) {
        if (this.state.sortBy === rowIndex) {
            this.state.sortOrder = this.state.sortOrder === "asc" ? "desc" : "asc";
        }
        this.state.sortBy = rowIndex;
    }

    getSortIcon(rowIndex) {
        if (this.state.sortBy !== rowIndex) {
            return "fa fa-sort";
        } else if (this.state.sortOrder === "asc") {
            return "fa fa-sort-asc";
        } else {
            return "fa fa-sort-desc";
        }
    }

    goToModel(model) {
        this.env.modelStore.setActiveModel({ model });
    }
}
