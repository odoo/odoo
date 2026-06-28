import { useRef } from "@web/owl2/utils";
import { Component, computed, proxy, useListener } from "@odoo/owl";
import { localeCompare } from "@web/core/l10n/utils";

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

    items = computed(() => this.computeItems());

    setup() {
        this.subTableRef = useRef("subTableRef");
        this.tooltipRef = useRef("tooltipRef");
        this.state = proxy({
            sortBy: 0,
            sortOrder: "desc",
            subTable: undefined,
            tooltipContent: "",
            tooltipStyle: "",
        });
        this.isHovering = false;
        this.hideTimeout = null;
        this.requestAnim = null;

        useListener(window, "click", (event) => {
            if (
                this.subTableRef.el &&
                this.subTableRef.el !== event.target &&
                !this.subTableRef.el.contains(event.target)
            ) {
                this.state.subTable = null;
            }
        });

        useListener(window, "scroll", () => (this.state.subTable = null));
    }

    showDynamicTooltip(event, content) {
        if (this.requestAnim) cancelAnimationFrame(this.requestAnim);
        if (this.hideTimeout) clearTimeout(this.hideTimeout);

        this.activeHoverTarget = event.target;
        this.isHovering = true;

        const triggerRect = event.target.getBoundingClientRect();

        this.requestAnim = requestAnimationFrame(() => {
            if (!this.tooltipRef.el || !this.isHovering) {
                return;
            }
            const top = triggerRect.top;
            const left = triggerRect.left + 20;

            this.state.tooltipContent = content;
            this.state.tooltipStyle = `
                top: ${top}px;
                left: ${left}px;
                opacity: 1;
                pointer-events: auto;
            `;
        });
    }

    scheduleHide(event) {
        if (this.hideTimeout) clearTimeout(this.hideTimeout);
        const currentTarget = event.target;
        this.isHovering = false;

        this.hideTimeout = setTimeout(() => {
            if (!this.isHovering) {
                this.state.tooltipStyle = `
                    top: ${this.tooltipRef.el ? this.tooltipRef.el.style.top : 0};
                    left: ${this.tooltipRef.el ? this.tooltipRef.el.style.left : 0};
                    opacity: 0;
                    pointer-events: none;
                `;
                setTimeout(() => {
                    if (currentTarget === this.activeHoverTarget) {
                        this.state.tooltipContent = "";
                    }
                }, 200);
            }
        }, 100);
    }

    keepAlive() {
        if (this.hideTimeout) clearTimeout(this.hideTimeout);
        this.isHovering = true;
    }

    computeItems() {
        if (this.state.sortBy >= 0) {
            const items = [...this.props.data.items];
            items.sort((itemA, itemB) => {
                const a = this.getValue(itemA[this.state.sortBy]);
                const b = this.getValue(itemB[this.state.sortBy]);
                if (this.state.sortOrder === "asc") {
                    return localeCompare(b, a);
                } else {
                    return localeCompare(a, b);
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
