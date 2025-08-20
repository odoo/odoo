import { Plugin } from "@html_editor/plugin";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { getDeepestPosition, isElement, isIconElement } from "@html_editor/utils/dom_info";
import { DIRECTIONS, nodeSize } from "@html_editor/utils/position";
import { closestElement } from "@html_editor/utils/dom_traversal";

export class BuilderSelectionRestrictionPlugin extends Plugin {
    static id = "builderSelectionRestriction";
    static dependencies = ["selection", "operation", "builderOptions"];

    resources = {
        // uncrossable_element_selector: CSS selectors of elements that should
        // not be crossed by the selection.
        uncrossable_element_selector: [
            "blockquote",
            "figcaption",
            "form",
            "div",
            "section",
            ".alert",
            ".row",
        ],
    };

    setup() {
        this.uncrossableSelectors = [
            ...new Set(this.getResource("uncrossable_element_selector")),
        ].join(", ");
        this.restrictedToPSelectors = [
            ...new Set(this.getResource("restricted_to_paragraph_blocks_selector")),
        ].join(", ");
        this.isCtrlAIgnoredPredicate = (selection) =>
            this.getResource("ignore_ctrl_a_predicates").some((fn) => fn(selection));

        // Check if the selection has been corrected to avoid multiple
        // corrections.
        this.isSelectionCorrected = false;

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

        // doing this manually instead of using addDomListener. This is because
        // addDomListener will ignore all events from protected targets. But in
        // our case, we still want to update the containers.
        this.onClick = this.onClick.bind(this);
        this.editable.addEventListener("click", this.onClick, { capture: true });
    }

    destroy() {
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
            if (this.isSelectionCorrected) {
                this.isSelectionCorrected = false;
                return;
            }
            this.dependencies.builderOptions.updateContainers(ev.target);
        });
    }

    /**
     * Manages the selection made with the "Control + A" key.
     */
    onCtrlAKeydown() {
        const { editableSelection, currentSelectionIsInEditable } =
            this.dependencies.selection.getSelectionData();
        const { anchorNode } = editableSelection;
        if (!currentSelectionIsInEditable || this.isCtrlAIgnoredPredicate(editableSelection)) {
            return;
        }

        const restrictingEl = this.getRestrictingElement(anchorNode);
        this.selectAllInElement(restrictingEl);
    }

    /**
     * Restricts the mouse selection inside paragraph or div.
     *
     * @param {Event} ev
     */
    restrictMouseSelection(ev) {
        const { editableSelection, currentSelectionIsInEditable } =
            this.dependencies.selection.getSelectionData();
        const { anchorNode } = editableSelection;
        if (!currentSelectionIsInEditable || editableSelection.isCollapsed) {
            return;
        }

        const restrictingEl = this.getRestrictingElement(anchorNode);
        this.restrictSelectionInElement(editableSelection, restrictingEl);
    }

    /**
     * Extend the selection to the whole element side by aide to properly
     * handle uncrossable elements, see uncrossable_element_selector.
     *
     * @param {Element} element
     */
    selectAllInElement(element) {
        let selection = this.dependencies.selection.getEditableSelection();
        const { focusNode, focusOffset } = selection;

        const [newAnchorNode, newAnchorOffset] = getDeepestPosition(element, 0);
        const [newFocusNode, newFocusOffset] = getDeepestPosition(element, nodeSize(element));

        // First extend the selection to the start of the element from the
        // focusNode.
        this.dependencies.selection.setSelection({
            anchorNode: focusNode,
            anchorOffset: focusOffset,
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
    }

    /**
     * Returns the element in which the selection should be restricted (by
     * default, the closest `div` element).
     *
     * @param {Node} anchorNode the current selection anchorNode
     * @returns {HTMLElement}
     */
    getRestrictingElement(anchorNode) {
        // Check if the selection is inside a special block that we need to
        // restrict to paragraph blocks.
        const closestDivEl = closestElement(anchorNode, "div");

        if (this.restrictedToPSelectors) {
            const closestPRestrictedEl = closestElement(anchorNode, this.restrictedToPSelectors);
            if (closestPRestrictedEl && !closestPRestrictedEl.contains(closestDivEl)) {
                return closestElement(anchorNode, "p");
            }
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
     * Corrects the current editablale selection if any uncrossable element is
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
            this.dependencies.builderOptions.updateContainers(
                closestElement(selection.commonAncestorContainer)
            );
            this.isSelectionCorrected = true;
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
                let newfocusNode, newfocusOffset;
                // the selection is inside one uncrossable node, no need to
                // correct it
                if (node.contains(anchorNode) && node.contains(focusNode)) {
                    break;
                } else if (!node.contains(anchorNode)) {
                    // the node is not the first selected node and it's
                    // uncrossable, we need to move the focusNode
                    // before/after this uncrossable node
                    if (direction === DIRECTIONS.RIGHT) {
                        tempFocusNode = node.previousElementSibling || tempFocusNode;
                        [newfocusNode, newfocusOffset] = getDeepestPosition(
                            tempFocusNode,
                            nodeSize(tempFocusNode)
                        );
                    } else {
                        tempFocusNode = node.nextElementSibling || tempFocusNode;
                        [newfocusNode, newfocusOffset] = getDeepestPosition(tempFocusNode, 0);
                    }

                    selection = this.dependencies.selection.setSelection({
                        anchorNode,
                        anchorOffset,
                        focusNode: newfocusNode,
                        focusOffset: newfocusOffset,
                    });
                } else {
                    // the node is the first selected node and it's uncrossable,
                    // we need to move the focusNode to the end/start of the
                    // uncrossable node
                    if (direction === DIRECTIONS.RIGHT) {
                        [newfocusNode, newfocusOffset] = getDeepestPosition(node, nodeSize(node));
                    } else {
                        [newfocusNode, newfocusOffset] = getDeepestPosition(node, 0);
                    }

                    selection = this.dependencies.selection.setSelection({
                        anchorNode,
                        anchorOffset,
                        focusNode: newfocusNode,
                        focusOffset: newfocusOffset,
                    });
                    break;
                }
            } else {
                tempFocusNode = node;
            }
        }

        this.dependencies.builderOptions.updateContainers(
            closestElement(selection.commonAncestorContainer)
        );
        this.isSelectionCorrected = true;
    }
}
