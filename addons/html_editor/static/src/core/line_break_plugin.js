import { splitTextNode } from "@html_editor/utils/dom";
import { Plugin } from "../plugin";
import { CTGROUPS, CTYPES } from "../utils/content_types";
import { getState, isFakeLineBreak, prepareUpdate } from "../utils/dom_state";
import { DIRECTIONS, leftPos, rightPos } from "../utils/position";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { closestBlock, isBlock } from "../utils/blocks";
import { nextLeaf } from "../utils/dom_info";

/**
 * @typedef { Object } LineBreakShared
 * @property { LineBreakPlugin['insertLineBreak'] } insertLineBreak
 * @property { LineBreakPlugin['insertLineBreakElement'] } insertLineBreakElement
 * @property { LineBreakPlugin['insertLineBreakNode'] } insertLineBreakNode
 */

export class LineBreakPlugin extends Plugin {
    static dependencies = ["selection", "history", "input", "delete"];
    static id = "lineBreak";
    static shared = ["insertLineBreak", "insertLineBreakNode", "insertLineBreakElement"];
    resources = {
        beforeinput_handlers: this.onBeforeInput.bind(this),
        legit_feff_predicates: [
            (node) =>
                !node.nextSibling &&
                !isBlock(closestElement(node)) &&
                nextLeaf(node, closestBlock(node)),
        ],
    };

    insertLineBreak() {
        this.dispatchTo("before_line_break_handlers");
        let selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
        if (!selection.isCollapsed) {
            // @todo @phoenix collapseIfZWS is not tested
            // this.shared.collapseIfZWS();
            this.dependencies.delete.deleteSelection();
            selection = this.dependencies.selection.getEditableSelection();
        }

        const targetNode = selection.anchorNode;
        const targetOffset = selection.anchorOffset;

        this.insertLineBreakNode({ targetNode, targetOffset });
        this.dependencies.history.addStep();
    }

    /**
     * @param {Object} params
     * @param {Node} params.targetNode
     * @param {number} params.targetOffset
     */
    insertLineBreakNode({ targetNode, targetOffset }) {
        const closestEl = closestElement(targetNode);
        if (closestEl && !closestEl.isContentEditable) {
            return;
        }
        if (targetNode.nodeType === Node.TEXT_NODE) {
            targetOffset = splitTextNode(targetNode, targetOffset);
            targetNode = targetNode.parentElement;
        }

        if (this.delegateTo("insert_line_break_element_overrides", { targetNode, targetOffset })) {
            return;
        }

        this.insertLineBreakElement({ targetNode, targetOffset });
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.targetNode
     * @param {number} params.targetOffset
     */
    insertLineBreakElement({ targetNode, targetOffset }) {
        const closestEl = closestElement(targetNode);
        if (closestEl && !closestEl.isContentEditable) {
            return;
        }
        const restore = prepareUpdate(targetNode, targetOffset);

        const brEl = this.document.createElement("br");
        const brEls = [brEl];
        if (targetOffset >= targetNode.childNodes.length) {
            targetNode.appendChild(brEl);
            if (
                !isBlock(closestElement(targetNode)) &&
                nextLeaf(targetNode, closestBlock(targetNode))
            ) {
                targetNode.appendChild(this.document.createTextNode("\uFEFF"));
            }
        } else {
            targetNode.insertBefore(brEl, targetNode.childNodes[targetOffset]);
        }
        if (
            isFakeLineBreak(brEl) &&
            !(getState(...leftPos(brEl), DIRECTIONS.LEFT).cType & (CTGROUPS.BLOCK | CTYPES.BR))
        ) {
            const brEl2 = this.document.createElement("br");
            brEl.before(brEl2);
            brEls.unshift(brEl2);
        }

        restore();

        // @todo ask AGE about why this code was only needed for unbreakable.
        // See `this._applyCommand('oEnter') === UNBREAKABLE_ROLLBACK_CODE` in
        // web_editor. Because now we should have a strong handling of the link
        // selection with the link isolation, if we want to insert a BR outside,
        // we can move the cursor outside the link.
        // So if there is no reason to keep this code, we should remove it.
        //
        // const anchor = brEls[0].parentElement;
        // // @todo @phoenix should this case be handled by a LinkPlugin?
        // // @todo @phoenix Don't we want this for all spans ?
        // if (anchor.nodeName === "A" && brEls.includes(anchor.firstChild)) {
        //     brEls.forEach((br) => anchor.before(br));
        //     const pos = rightPos(brEls[brEls.length - 1]);
        //     this.dependencies.selection.setSelection({ anchorNode: pos[0], anchorOffset: pos[1] });
        // } else if (anchor.nodeName === "A" && brEls.includes(anchor.lastChild)) {
        //     brEls.forEach((br) => anchor.after(br));
        //     const pos = rightPos(brEls[0]);
        //     this.dependencies.selection.setSelection({ anchorNode: pos[0], anchorOffset: pos[1] });
        // }
        for (const el of brEls) {
            // @todo @phoenix we don t want to setSelection multiple times
            if (el.parentNode) {
                const pos = rightPos(el);
                this.dependencies.selection.setSelection({
                    anchorNode: pos[0],
                    anchorOffset: pos[1],
                });
                break;
            }
        }
    }

    onBeforeInput(e) {
        if (e.inputType === "insertLineBreak") {
            e.preventDefault();
            this.insertLineBreak();
        }
    }
}
