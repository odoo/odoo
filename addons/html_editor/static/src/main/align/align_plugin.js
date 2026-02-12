import { reactive } from "@web/owl2/utils";
import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { isVisibleTextNode } from "@html_editor/utils/dom_info";
import { _t } from "@web/core/l10n/translation";
import { AlignSelector } from "./align_selector";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { weakMemoize } from "@html_editor/utils/functions";

const alignmentItems = [
    // In RTL, left and right icons are reverted to represent start and end.
    { icon: "left", mode: "start", description: _t("Left align") },
    { icon: "center", mode: "center", description: _t("Center align") },
    { icon: "right", mode: "end", description: _t("Right align") },
    { icon: "justify", mode: "justify", description: _t("Justify") },
];

export class AlignPlugin extends Plugin {
    static id = "align";
    static dependencies = ["history", "selection"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "alignStart",
                run: () => this.setAlignment("start"),
                isAvailable: this.canSetAlignment.bind(this),
            },
            {
                id: "alignCenter",
                run: () => this.setAlignment("center"),
                isAvailable: this.canSetAlignment.bind(this),
            },
            {
                id: "alignEnd",
                run: () => this.setAlignment("end"),
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

    get alignmentIconMode() {
        const sel = this.dependencies.selection.getSelectionData().deepEditableSelection;
        const block = closestBlock(sel?.anchorNode);
        let { direction, textAlign } = getComputedStyle(block);
        if (direction === "rtl") {
            // Handle compatibility:
            // in RTL "left" is equivalent to "end"
            // and "right" is equivalent to "start"
            if (textAlign === "left") {
                textAlign = "end";
            } else if (textAlign === "right") {
                textAlign = "start";
            }
        }
        if (textAlign === "end") {
            // The icon name suffix for "end" is "right", both in LTR and RTL
            return "right";
        }
        // Return only one of the four supported icon name suffixes, defaulting
        // to "left" which is also used for "start" in both LTR and RTL
        return ["center", "right", "justify"].includes(textAlign) ? textAlign : "left";
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
                const { textAlign } = getComputedStyle(block);
                if (textAlign !== mode) {
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
        this.alignment.displayName = this.alignmentIconMode;
    }
}
