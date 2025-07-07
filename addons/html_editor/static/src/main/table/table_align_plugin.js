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
                        .getTargetedNodes()
                        .some((node) => closestElement(node, "td, th")),
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
        remove_all_formats_handlers: this.setVerticalAlignment.bind(this),

        /** Predicates */
        has_format_predicates: (node) => closestElement(node, "td, th")?.style.verticalAlign,
    };

    setup() {
        this.verticalAlignMode = reactive({ displayName: "" });
    }

    get currentVerticalAlign() {
        const targetedCells = this.dependencies.selection
            .getTargetedNodes()
            .map((node) => closestElement(node, "td, th"))
            .filter(Boolean);

        if (!targetedCells.length) {
            return "";
        }

        const verticalAlign = targetedCells[0].style.verticalAlign;
        return verticalAlign &&
            targetedCells.every((cell) => cell.style.verticalAlign === verticalAlign)
            ? verticalAlign
            : "";
    }

    setVerticalAlignment(mode = "") {
        const targetedCells = new Set(
            this.dependencies.selection
                .getTargetedNodes()
                .map((node) => closestElement(node, "td, th"))
                .filter(Boolean)
        );
        let isAlignmentUpdated = false;

        for (const cell of targetedCells) {
            if (cell.isContentEditable && cell.style.verticalAlign !== mode) {
                cell.style.verticalAlign = mode;
                isAlignmentUpdated = true;
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
