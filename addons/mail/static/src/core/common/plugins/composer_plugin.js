import { Plugin } from "@html_editor/plugin";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { childNodes } from "@html_editor/utils/dom_traversal";

/**
 * @param {SelectionData} selectionData
 */
function target(selectionData, editable) {
    if (childNodes(editable).length !== 1) {
        return;
    }
    const node = selectionData.editableSelection.anchorNode;
    const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    if (
        selectionData.documentSelectionIsInEditable &&
        (el.tagName === "DIV" || el.tagName === "P") &&
        isEmptyBlock(el)
    ) {
        return el;
    }
}

export class ComposerPlugin extends Plugin {
    static id = "composer";
    static dependencies = ["history", "dom", "clipboard", "hint", "input"];
    resources = {
        before_paste_handlers: this.config.composerPLuginDependencies.onBeforePaste,
        hints: {
            text: this.config.composerPLuginDependencies.placeholder,
            target,
        },
        input_handlers: this.config.composerPLuginDependencies.onInput,
    };

    setup() {
        this.addDomListener(
            this.editable,
            "keydown",
            this.config.composerPLuginDependencies.onKeydown
        );
        this.addDomListener(
            this.editable,
            "focusin",
            this.config.composerPLuginDependencies.onFocusin
        );
        this.addDomListener(
            this.editable,
            "focusout",
            this.config.composerPLuginDependencies.onFocusout
        );
    }
}
