import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { isVisibleTextNode } from "@html_editor/utils/dom_info";
import { _t } from "@web/core/l10n/translation";
import { AlignSelector } from "./align_selector";
import { reactive } from "@odoo/owl";
import { isListItem } from "../list/utils";

const alignmentItems = [
    { mode: "left" },
    { mode: "center" },
    { mode: "right" },
    { mode: "justify" },
];

export class AlignPlugin extends Plugin {
    static id = "align";
    static dependencies = ["history", "selection"];
    resources = {
        user_commands: [
            {
                id: "alignLeft",
                run: () => this.setAlignment("left"),
            },
            {
                id: "alignCenter",
                run: () => this.setAlignment("center"),
            },
            {
                id: "alignRight",
                run: () => this.setAlignment("right"),
            },
            {
                id: "justify",
                run: () => this.setAlignment("justify"),
            },
        ],
        shortcuts: [
            { hotkey: "control+shift+l", commandId: "alignLeft" },
            { hotkey: "control+shift+e", commandId: "alignCenter" },
            { hotkey: "control+shift+r", commandId: "alignRight" },
            { hotkey: "control+shift+j", commandId: "justify" },
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
            },
        ],

        /** Handlers */
        selectionchange_handlers: this.updateAlignmentParams.bind(this),
        post_undo_handlers: this.updateAlignmentParams.bind(this),
        post_redo_handlers: this.updateAlignmentParams.bind(this),
        remove_format_handlers: this.setAlignment.bind(this),

        /** Predicates */
        has_format_predicates: (node) => closestBlock(node)?.style.textAlign,
    };

    setup() {
        this.alignment = reactive({ displayName: "" });
    }

    get alignmentMode() {
        const sel = this.dependencies.selection.getSelectionData().deepEditableSelection;
        const block = closestBlock(sel?.anchorNode);
        const textAlign = this.getTextAlignment(block);
        return ["center", "right", "justify"].includes(textAlign) ? textAlign : "left";
    }

    getTextAlignment(block) {
        const getAlignement = (block) => {
            const { textAlign, alignSelf } = getComputedStyle(block);
            if (
                block.nodeName === "LI" &&
                ["flex-start", "flex-end", "center"].includes(alignSelf)
            ) {
                return alignSelf.replace("flex-", "");
            }
            return textAlign;
        };
        const { direction } = getComputedStyle(block);
        if (getAlignement(block) === "start") {
            return direction === "rtl" ? "right" : "left";
        } else if (getAlignement(block) === "end") {
            return direction === "rtl" ? "left" : "right";
        }
        return getAlignement(block);
    }

    setAlignment(mode = "") {
        const visitedBlocks = new Set();
        const traversedNode = this.dependencies.selection.getTraversedNodes();
        let isAlignmentUpdated = false;

        for (const node of traversedNode) {
            if (isVisibleTextNode(node) || node.nodeName === "BR") {
                const block = closestBlock(node);
                if (!visitedBlocks.has(block)) {
                    const currentTextAlign = this.getTextAlignment(block);
                    if (currentTextAlign !== mode && block.isContentEditable) {
                        if (isListItem(block)) {
                            this.dispatchTo("align_handlers", block, mode);
                        } else {
                            block.style.textAlign = mode;
                        }
                        isAlignmentUpdated = true;
                    }
                    visitedBlocks.add(block);
                }
            }
        }
        if (isAlignmentUpdated) {
            this.dependencies.history.addStep();
        }
        this.updateAlignmentParams();
    }

    updateAlignmentParams() {
        this.alignment.displayName = this.alignmentMode;
    }
}
