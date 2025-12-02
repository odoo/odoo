import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { isVisibleTextNode } from "@html_editor/utils/dom_info";
import { _t } from "@web/core/l10n/translation";
import { AlignSelector } from "./align_selector";
import { reactive } from "@odoo/owl";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { weakMemoize } from "@html_editor/utils/functions";

const alignmentItems = [
    { mode: "left" },
    { mode: "center" },
    { mode: "right" },
    { mode: "justify" },
];

export class AlignPlugin extends Plugin {
    static id = "align";
    static dependencies = ["history", "selection"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "alignLeft",
                run: () => this.setAlignment("left"),
                isAvailable: this.canSetAlignment.bind(this),
            },
            {
                id: "alignCenter",
                run: () => this.setAlignment("center"),
                isAvailable: this.canSetAlignment.bind(this),
            },
            {
                id: "alignRight",
                run: () => this.setAlignment("right"),
                isAvailable: this.canSetAlignment.bind(this),
            },
            {
                id: "justify",
                run: () => this.setAlignment("justify"),
                isAvailable: this.canSetAlignment.bind(this),
            },
        ],
        toolbar_items: [
            {
                id: "alignment",
                groupId: "layout",
                description: _t("Align text"),
                Component: AlignSelector,
                props: {
                    getItems: () => alignmentItems,
                    getDisplay: () => this.alignment,
                    onSelected: (item) => {
                        this.setAlignment(item.mode);
                    },
                },
                isAvailable: this.canSetAlignment.bind(this),
            },
        ],

        /** Handlers */
        selectionchange_handlers: this.updateAlignmentParams.bind(this),
        post_undo_handlers: this.updateAlignmentParams.bind(this),
        post_redo_handlers: this.updateAlignmentParams.bind(this),
        remove_all_formats_handlers: this.setAlignment.bind(this),

        /** Predicates */
        has_format_predicates: (node) => closestBlock(node)?.style.textAlign,
    };

    setup() {
        this.alignment = reactive({ displayName: "" });
        this.canSetAlignmentMemoized = weakMemoize(
            (selection) => isHtmlContentSupported(selection) && this.getBlocksToAlign().length > 0
        );
    }

    get alignmentMode() {
        const sel = this.dependencies.selection.getSelectionData().deepEditableSelection;
        const block = closestBlock(sel?.anchorNode);
        const textAlign = this.getTextAlignment(block);
        return ["center", "right", "justify"].includes(textAlign) ? textAlign : "left";
    }

    getTextAlignment(block) {
        const { direction, textAlign } = getComputedStyle(block);
        if (textAlign === "start") {
            return direction === "rtl" ? "right" : "left";
        } else if (textAlign === "end") {
            return direction === "rtl" ? "left" : "right";
        }
        return textAlign;
    }

    getBlocksToAlign() {
        return this.dependencies.selection
            .getTargetedNodes()
            .filter((node) => isVisibleTextNode(node) || node.nodeName === "BR")
            .map((node) => closestBlock(node))
            .filter((block) => block.isContentEditable);
    }

    setAlignment(mode = "") {
        const visitedBlocks = new Set();
        let isAlignmentUpdated = false;

        for (const block of this.getBlocksToAlign()) {
            if (!visitedBlocks.has(block)) {
                const currentTextAlign = this.getTextAlignment(block);
                if (currentTextAlign !== mode) {
                    block.style.textAlign = mode;
                    isAlignmentUpdated = true;
                }
                visitedBlocks.add(block);
            }
        }
        if (mode && isAlignmentUpdated) {
            this.dependencies.history.addStep();
        }
        this.updateAlignmentParams();
    }

    canSetAlignment(selection) {
        return this.canSetAlignmentMemoized(selection);
    }

    updateAlignmentParams() {
        this.alignment.displayName = this.alignmentMode;
    }
}
