import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { _t } from "@web/core/l10n/translation";
import { reactive } from "@odoo/owl";
import { TableAlignSelector } from "./table_align_selector";

const verticalAlignmentItems = [
    {
        mode: "top",
        template: "html_editor.VerticalAlignTop",
    },
    {
        mode: "middle",
        template: "html_editor.VerticalAlignMiddle",
    },
    {
        mode: "bottom",
        template: "html_editor.VerticalAlignBottom",
    },
];

export class TableAlignPlugin extends Plugin {
    static id = "tableAlign";
    static dependencies = ["history", "selection"];

    resources = {
        user_commands: [
            {
                id: "alignTop",
                run: () => this.setVerticalAlignment("top"),
            },
            {
                id: "alignMiddle",
                run: () => this.setVerticalAlignment("middle"),
            },
            {
                id: "alignBottom",
                run: () => this.setVerticalAlignment("bottom"),
            },
        ],
        toolbar_items: [
            {
                id: "table_alignment",
                groupId: "layout",
                description: _t("Vertical align table cells content"),
                isAvailable: () =>
                    this.dependencies.selection
                        .getTraversedNodes()
                        .some((node) => ["TD", "TH"].includes(node.nodeName)),
                Component: TableAlignSelector,
                props: {
                    getItems: () => verticalAlignmentItems,
                    getDisplay: () => this.verticalAlignMode,
                    onSelected: (item) => {
                        this.setVerticalAlignment(item.mode);
                    },
                },
            },
        ],

        /** Handlers */
        selectionchange_handlers: this.updateVerticalAlignParams.bind(this),
        post_undo_handlers: this.updateVerticalAlignParams.bind(this),
        post_redo_handlers: this.updateVerticalAlignParams.bind(this),
        remove_format_handlers: this.setVerticalAlignment.bind(this),

        has_format_predicates: (node) => closestElement(node, "td,th")?.style.verticalAlign,
    };

    setup() {
        this.verticalAlignMode = reactive({ displayName: "" });
    }

    get currentVerticalAlign() {
        const cell = this.dependencies.selection
            .getTraversedNodes()
            .find((n) => n.nodeType === Node.ELEMENT_NODE && ["TD", "TH"].includes(n.tagName));
        return cell?.style.verticalAlign || "top";
    }

    setVerticalAlignment(mode = "") {
        const visitedCells = new Set();
        const traversedNode = this.dependencies.selection.getTraversedNodes();
        let isAlignmentUpdated = false;

        for (const node of traversedNode) {
            const cell = closestElement(node, "td,th");
            if (cell && !visitedCells.has(cell) && cell.isContentEditable) {
                if (cell.style.verticalAlign !== mode) {
                    cell.style.verticalAlign = mode;
                    isAlignmentUpdated = true;
                }
                visitedCells.add(cell);
            }
        }
        if (isAlignmentUpdated) {
            this.dependencies.history.addStep();
        }
        this.updateVerticalAlignParams();
    }

    updateVerticalAlignParams() {
        this.verticalAlignMode.displayName = this.currentVerticalAlign;
    }
}
