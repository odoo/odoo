import { Plugin } from "@html_editor/plugin";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { getDeepestPosition, isElement, isIconElement } from "@html_editor/utils/dom_info";
import { DIRECTIONS, nodeSize } from "@html_editor/utils/position";
import { closestElement } from "@html_editor/utils/dom_traversal";

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef {CSSSelector[]} uncrossable_element_selector
 * CSS selectors of elements that should not be crossed by the selection.
 *
 * @typedef {((selection: EditorSelection) => boolean)[]} ignore_ctrl_a_predicates
 * Cases where nothing should be done when pressing ctrl + a.
 */

export class BuilderSelectionRestrictionPlugin extends Plugin {
    static id = "builderSelectionRestriction";
    static dependencies = ["selection", "operation", "builderOptions"];

    /** @type {import("plugins").BuilderResources} */
    resources = {
        uncrossable_element_selector: ["blockquote", "form", "div", "section", ".row"],
    };

    setup() {
        this.uncrossableSelectors = this.getResource("uncrossable_element_selector").join(", ");
        this.isCtrlAIgnored = (selection) =>
            this.checkPredicates("ignore_ctrl_a_predicates", selection) ?? false;

        // Tell if the containers should be/were updated with the corrected
        // selection
        this.shouldUpdateContainersWithSelection = false;

        this.addDomListener(this.editable.ownerDocument, "keydown", (ev) => {
            if (getActiveHotkey(ev) !== "control+a") {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            this.onCtrlAKeydown();
        });
        this.addDomListener(this.document, "mouseup", this.restrictMouseSelection);
        this.addDomListener(this.document, "touchend", this.restrictMouseSelection);

        // Doing this manually instead of using addDomListener. This is because
        // addDomListener will ignore all events from protected targets. But in
        // our case, we still want to update the containers.
        this.onClick = this.onClick.bind(this);
        this.editable.addEventListener("click", this.onClick, { capture: true });
    }

    destroy() {
        super.destroy();
        this.editable.removeEventListener("click", this.onClick, { capture: true });
    }

    /**
     * Activates the options of the clicked element.
     * Note: if the selection was corrected, the click is ignored, as the
     * selection already managed it.
     *
     * @param {Event} ev
     */
    onClick(ev) {
        this.dependencies.operation.next(() => {
            if (this.shouldUpdateContainersWithSelection) {
                this.shouldUpdateContainersWithSelection = false;
                return;
            }
            this.dependencies.builderOptions.updateContainers(ev.target);
        });
    }

    /**
     * Manages the selection made with the "Control + A" key.
     */
    onCtrlAKeydown() {
        const { editableSelection, documentSelectionIsInEditable } =
            this.dependencies.selection.getSelectionData();
        const currentSelectionIsInEditable =
            documentSelectionIsInEditable && this.dependencies.selection.editableDocumentHasFocus();
        const { anchorNode } = editableSelection;
        if (!currentSelectionIsInEditable || this.isCtrlAIgnored(editableSelection)) {
            return;
        }

        // Restrict the selection to not select the whole document.
        const restrictingEl = this.getRestrictingElement(anchorNode);
        this.selectAllInElement(restrictingEl);
        if (this.shouldUpdateContainersWithSelection) {
            const selection = this.dependencies.selection.getEditableSelection();
            this.dependencies.builderOptions.updateContainers(
                closestElement(selection.commonAncestorContainer)
            );
            this.shouldUpdateContainersWithSelection = false;
        }
    }

    /**
     * Restricts the mouse selection inside the closest div.
     *
     * @param {Event} ev
     */
    restrictMouseSelection(ev) {
        const { editableSelection, documentSelectionIsInEditable } =
            this.dependencies.selection.getSelectionData();
        const currentSelectionIsInEditable =
            documentSelectionIsInEditable && this.dependencies.selection.editableDocumentHasFocus();
        const { anchorNode } = editableSelection;
        if (!currentSelectionIsInEditable || editableSelection.isCollapsed) {
            return;
        }

        const restrictingEl = this.getRestrictingElement(anchorNode);
        this.restrictSelectionInElement(editableSelection, restrictingEl);
        if (this.shouldUpdateContainersWithSelection) {
            const selection = this.dependencies.selection.getEditableSelection();
            this.dependencies.builderOptions.updateContainers(
                closestElement(selection.commonAncestorContainer)
            );
        }
    }

    /**
     * Extends the selection to the whole element, while properly handling
     * the uncrossable elements.
     *
     * @param {Element} element
     */
    selectAllInElement(element) {
        let selection = this.dependencies.selection.getEditableSelection();

        const [newAnchorNode, newAnchorOffset] = getDeepestPosition(element, 0);
        const [newFocusNode, newFocusOffset] = getDeepestPosition(element, nodeSize(element));

        // First extend the selection to the start of the element from the
        // focusNode.
        this.dependencies.selection.setSelection({
            anchorNode: selection.focusNode,
            anchorOffset: selection.focusOffset,
            focusNode: newAnchorNode,
            focusOffset: newAnchorOffset,
        });
        // Then correct the selection if some uncrossable elements are crossed
        // on the extended part.
        this.correctSelectionOnUncrossable();

        // Get the fixed extended selection after the first step, and then
        // extend it to the end of the element.
        selection = this.dependencies.selection.getEditableSelection();
        this.dependencies.selection.setSelection({
            anchorNode: selection.focusNode,
            anchorOffset: selection.focusOffset,
            focusNode: newFocusNode,
            focusOffset: newFocusOffset,
        });
        // Finally correct the selection if some uncrossable elements are
        // crossed on the extended part.
        this.correctSelectionOnUncrossable();

        // Make sure the selection does not contain uncrossable elements. We
        // limit this to 5 attempts to not block the editor (it is very unlikely
        // to have more than 5 nested uncrossable elements, so 5 is acceptable).
        selection = this.dependencies.selection.getEditableSelection();
        let attemptsLeft = 5;
        while (
            closestElement(selection.anchorNode, this.uncrossableSelectors) !==
                closestElement(selection.focusNode, this.uncrossableSelectors) &&
            attemptsLeft
        ) {
            this.correctSelectionOnUncrossable();
            selection = this.dependencies.selection.getEditableSelection();
            attemptsLeft -= 1;
        }
    }

    /**
     * Returns the element in which the selection should be restricted (by
     * default, the closest `div` element).
     *
     * @param {Node} anchorNode the current selection anchorNode
     * @returns {HTMLElement}
     */
    getRestrictingElement(anchorNode) {
        const closestDivEl = closestElement(anchorNode, "div");

        if (!closestDivEl) {
            console.warn(
                "The anchordeNode of the selection is not inside a <div> element, the selection restriction plugin might not work properly",
                anchorNode
            );
            return closestElement(anchorNode);
        }
        return closestDivEl;
    }

    /**
     * Restricts the selection inside a given element.
     *
     * @param {Selection} selection
     * @param {Element} elementEl element in which selection will be restricted
     */
    restrictSelectionInElement(selection, elementEl) {
        const { anchorNode, anchorOffset, focusNode, direction } = selection;
        const isFocusInBlock = elementEl.contains(focusNode);

        // If the focus node is not in the block, we need to put it inside the
        // elementEl. If the selection is left to right, we put it at the end of
        // the block, otherwise at the start of the block.
        if (!isFocusInBlock) {
            let focusNode, focusOffset;
            if (direction === DIRECTIONS.RIGHT) {
                [focusNode, focusOffset] = getDeepestPosition(elementEl, nodeSize(elementEl));
            } else {
                [focusNode, focusOffset] = getDeepestPosition(elementEl, 0);
            }
            this.dependencies.selection.setSelection({
                anchorNode,
                anchorOffset,
                focusNode,
                focusOffset,
            });
        }
        // Finally, we correct the selection if some uncrossable elements are
        // crossed.
        this.correctSelectionOnUncrossable();
    }

    /**
     * Checks if the the given node is uncrossable or inside an uncrossable. If
     * so, checks if the selected nodes contains the uncrossable.
     *
     * @param {Node} node
     * @param {Array<Node>} selectedNodes
     * @returns {Boolean}
     */
    isNodeSelectionUncrossable(node, selectedNodes) {
        const closestUncrossableEl = closestElement(node, this.uncrossableSelectors);
        if (closestUncrossableEl) {
            return node === closestUncrossableEl || selectedNodes.includes(closestUncrossableEl);
        }

        return false;
    }

    /**
     * Corrects the current editable selection if any uncrossable element is
     * crossed, see uncrossable_element_selector.
     */
    correctSelectionOnUncrossable() {
        let selection = this.dependencies.selection.getEditableSelection();
        const { anchorNode, anchorOffset, focusNode, direction } = selection;
        const selectedNodes = this.dependencies.selection
            .getTargetedNodes(selection)
            .filter(isElement);
        if (direction !== DIRECTIONS.RIGHT) {
            selectedNodes.reverse();
        }

        // Do not correct the selection if the only selected node is an image or
        // an icon, otherwise it would break their option containers (because we
        // force the selection to be around them when we click on them).
        if (
            selectedNodes.length === 1 &&
            (selectedNodes[0].tagName === "IMG" || isIconElement(selectedNodes[0]))
        ) {
            return;
        }
        // If no uncrossable element is selected, no need to correct the
        // selection.
        if (selectedNodes.every((node) => !node.matches(this.uncrossableSelectors))) {
            this.shouldUpdateContainersWithSelection = true;
            return;
        }

        // This for loop checks for the first uncrossable element in the
        // selection based on the selection direction. If an uncrossable is
        // found that is crossed by the selection, the selection is
        // corrected to be just before or after the uncrossable element based on
        // the selection direction.
        let tempFocusNode;
        for (const node of selectedNodes) {
            if (this.isNodeSelectionUncrossable(node, selectedNodes)) {
                let newFocusNode, newFocusOffset;
                const closestUncrossableEl = closestElement(node, this.uncrossableSelectors);
                if (!node.contains(anchorNode)) {
                    // If the anchor is inside the same uncrossable ancestor as
                    // this node, no boundary is being crossed, both anchor and
                    // node are on the same side, so we skip it.
                    if (
                        closestUncrossableEl !== node &&
                        closestUncrossableEl.contains(anchorNode)
                    ) {
                        tempFocusNode = node;
                        continue;
                    }
                    // The node is not the first selected node and it's
                    // uncrossable, we need to move the focusNode before
                    // this uncrossable node (or after if we are selecting to
                    // the left).
                    if (direction === DIRECTIONS.RIGHT) {
                        tempFocusNode = node.previousElementSibling || tempFocusNode;
                        [newFocusNode, newFocusOffset] = getDeepestPosition(
                            tempFocusNode,
                            nodeSize(tempFocusNode)
                        );
                    } else {
                        tempFocusNode = node.nextElementSibling || tempFocusNode;
                        [newFocusNode, newFocusOffset] = getDeepestPosition(tempFocusNode, 0);
                    }

                    selection = this.dependencies.selection.setSelection({
                        anchorNode,
                        anchorOffset,
                        focusNode: newFocusNode,
                        focusOffset: newFocusOffset,
                    });
                } else if (!node.contains(focusNode)) {
                    // We skip it if the focusNode is outside of the uncrossable
                    // ancestor.
                    if (
                        closestUncrossableEl !== node &&
                        !closestUncrossableEl.contains(focusNode)
                    ) {
                        tempFocusNode = node;
                        continue;
                    }
                    // The node is the first selected node and it's uncrossable,
                    // we need to move the focusNode to the end of the uncrossable
                    // node (or to the start if we are selecting to the left).
                    if (direction === DIRECTIONS.RIGHT) {
                        [newFocusNode, newFocusOffset] = getDeepestPosition(node, nodeSize(node));
                    } else {
                        [newFocusNode, newFocusOffset] = getDeepestPosition(node, 0);
                    }

                    selection = this.dependencies.selection.setSelection({
                        anchorNode,
                        anchorOffset,
                        focusNode: newFocusNode,
                        focusOffset: newFocusOffset,
                    });
                }
                break;
            } else {
                tempFocusNode = node;
            }
        }

        this.shouldUpdateContainersWithSelection = true;
    }
}
