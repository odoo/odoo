import { Plugin } from "@html_editor/plugin";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { getDeepestPosition } from "@html_editor/utils/dom_info";
import { DIRECTIONS, nodeSize } from "@html_editor/utils/position";
import { closestElement } from "@html_editor/utils/dom_traversal";

// we probably need to move these special blocks to a resource in different plugins
const SPECIAL_BLOCK_WITH_TEXT_IN_NON_DIV = ["BLOCKQUOTE"];
const UNCROSSABLE_ELEMENTS = ["BLOCKQUOTE", "FORM", "SECTION", "DIV"];
const UNCROSSABLE_ELEMENT_CLASSES = ["alert", "row"];

export class BuilderSelectionRestrictionPlugin extends Plugin {
    static id = "builderSelectionRestriction";
    static dependencies = ["history", "selection", "operation", "builderOptions"];

    resources = {
        uncrossable_elements: UNCROSSABLE_ELEMENTS,
        uncrossable_element_classes: UNCROSSABLE_ELEMENT_CLASSES,
        special_block_with_text_in_non_div: SPECIAL_BLOCK_WITH_TEXT_IN_NON_DIV,
    };

    setup() {
        Window.selection = this.dependencies.selection;
        this.uncrossable_elements = [...new Set(this.getResource("uncrossable_elements"))];
        this.uncrossable_element_classes = [
            ...new Set(this.getResource("uncrossable_element_classes")),
        ];
        this.special_block_with_text_in_non_div = [
            ...new Set(this.getResource("special_block_with_text_in_non_div")),
        ];
        this.selectionCorrected = false;

        this.addDomListener(this.editable, "keydown", this.onKeydown);
        this.addDomListener(this.editable, "mouseup", this.restrictSelectionInClosestDiv);
        this.addDomListener(this.editable, "touchend", this.restrictSelectionInClosestDiv);

        // doing this manually instead of using addDomListener. This is because
        // addDomListener will ignore all events from protected targets. But in
        // our case, we still want to update the containers.
        this.onClick = this.onClick.bind(this);
        this.editable.addEventListener("click", this.onClick, { capture: true });
    }

    destroy() {
        this.editable.removeEventListener("click", this.onClick, { capture: true });
    }

    onClick(ev) {
        this.dependencies.operation.next(() => {
            if (this.selectionCorrected) {
                this.selectionCorrected = false;
                return;
            }
            this.dependencies.builderOptions.updateContainers(ev.target);
        });
    }

    onKeydown(ev) {
        if (getActiveHotkey(ev) === "control+a") {
            const { editableSelection, currentSelectionIsInEditable } =
                this.dependencies.selection.getSelectionData();
            if (
                !currentSelectionIsInEditable ||
                // make it a resource for adding other cases?
                editableSelection.commonAncestorContainer.nodeName === "FIGURE"
            ) {
                ev.preventDefault();
                ev.stopPropagation();
                return;
            }
            ev.preventDefault();
            // make it a resource for adding other cases?
            const closestSpecialBlock = closestElement(
                editableSelection.anchorNode,
                this.special_block_with_text_in_non_div.join(",")
            );
            const closestDiv = closestElement(editableSelection.anchorNode, "div");

            // if the closest special block doesn't contains the closest div block,
            // we select the paragraph, otherwise we select the whole closest div block
            if (closestSpecialBlock && !closestSpecialBlock.contains(closestDiv)) {
                this.selectAllInElement(closestElement(editableSelection.anchorNode, "p"));
            } else {
                this.selectAllInElement(closestDiv);
            }
            ev.stopPropagation();
        }
    }

    // we extend the selection to the whole element step by step to properly
    // handle uncrossable elements (like row, blockquote...)
    selectAllInElement(element) {
        let selection = this.dependencies.selection.getEditableSelection();
        let { anchorNode, anchorOffset, focusNode, focusOffset, direction } = selection;

        const [newAnchorNode, newAnchorOffset] = getDeepestPosition(element, 0);
        const [newFocusNode, newFocusOffset] = getDeepestPosition(element, nodeSize(element));
        if (direction === DIRECTIONS.RIGHT) {
            this.dependencies.selection.setSelection({
                anchorNode: focusNode,
                anchorOffset: focusOffset,
                focusNode: newAnchorNode,
                focusOffset: newAnchorOffset,
            });
        } else {
            this.dependencies.selection.setSelection({
                anchorNode: anchorNode,
                anchorOffset: anchorOffset,
                focusNode: newAnchorNode,
                focusOffset: newAnchorOffset,
            });
        }
        this.correctSelectionOnUncrossable();
        selection = this.dependencies.selection.getEditableSelection();
        ({ focusNode, focusOffset } = selection);
        this.dependencies.selection.setSelection({
            anchorNode: focusNode,
            anchorOffset: focusOffset,
            focusNode: newFocusNode,
            focusOffset: newFocusOffset,
        });
        this.correctSelectionOnUncrossable();
    }

    restrictSelectionInElement(selection, block) {
        const { anchorNode, anchorOffset, focusNode, direction } = selection;
        const isFocusInBlock = block.contains(focusNode);

        if (!isFocusInBlock) {
            let focusNode, focusOffset;
            if (direction === DIRECTIONS.RIGHT) {
                [focusNode, focusOffset] = getDeepestPosition(block, nodeSize(block));
            } else {
                [focusNode, focusOffset] = getDeepestPosition(block, 0);
            }
            this.dependencies.selection.setSelection({
                anchorNode,
                anchorOffset,
                focusNode,
                focusOffset,
            });
        }
        this.correctSelectionOnUncrossable();
    }

    restrictSelectionInClosestDiv(ev) {
        const { editableSelection, currentSelectionIsInEditable } =
            this.dependencies.selection.getSelectionData();
        if (!currentSelectionIsInEditable) {
            return;
        }
        if (editableSelection.isCollapsed) {
            return;
        }

        // make it a resource for adding other cases?
        const closestSpecialBlock = closestElement(
            editableSelection.anchorNode,
            this.special_block_with_text_in_non_div.join(",")
        );
        const closestDiv = closestElement(editableSelection.anchorNode, "div");

        if (closestSpecialBlock && !closestSpecialBlock.contains(closestDiv)) {
            const closestParagraph = closestElement(editableSelection.anchorNode, "p");
            this.restrictSelectionInElement(editableSelection, closestParagraph);
        } else {
            this.restrictSelectionInElement(editableSelection, closestDiv);
        }
    }

    isNodeSelectionUncrossable(node, selectedNodes) {
        return (
            this.uncrossable_elements.includes(node.nodeName) ||
            this.uncrossable_elements.some((tagName) =>
                selectedNodes.includes(closestElement(node, tagName))
            ) ||
            this.uncrossable_element_classes.some(
                (className) =>
                    node.classList?.contains(className) ||
                    selectedNodes.includes(closestElement(node, `.${className}`))
            )
        );
    }

    correctSelectionOnUncrossable() {
        const selection = this.dependencies.selection.getEditableSelection();
        const { anchorNode, anchorOffset, focusNode, direction } = selection;
        const selectedNodes = this.dependencies.selection
            .getTargetedNodes(selection)
            .filter((node) => node.nodeType === Node.ELEMENT_NODE);
        const selectedNodesLooping =
            direction === DIRECTIONS.RIGHT ? selectedNodes : selectedNodes.reverse();

        // do not do selection correction if 1. the only selected node is an image cause we force
        // the selection to be around the image when clicking on it, correction would break the
        // option container for images 2. icon elements (i.fa, span.fa...)
        if (
            selectedNodesLooping.length === 1 &&
            (selectedNodesLooping[0].tagName === "IMG" ||
                selectedNodesLooping[0].classList?.contains("fa"))
        ) {
            return;
        }

        let temperaryFocusNode;
        for (const node of selectedNodesLooping) {
            if (this.isNodeSelectionUncrossable(node, selectedNodesLooping)) {
                if (node.contains(anchorNode) && node.contains(focusNode)) {
                    break;
                } else if (!node.contains(anchorNode)) {
                    let focusNode, focusOffset;
                    if (direction === DIRECTIONS.RIGHT) {
                        temperaryFocusNode = node.previousElementSibling
                            ? node.previousElementSibling
                            : temperaryFocusNode;
                        [focusNode, focusOffset] = getDeepestPosition(
                            temperaryFocusNode,
                            nodeSize(temperaryFocusNode)
                        );
                    } else {
                        temperaryFocusNode = node.nextElementSibling
                            ? node.nextElementSibling
                            : temperaryFocusNode;
                        [focusNode, focusOffset] = getDeepestPosition(temperaryFocusNode, 0);
                    }

                    const currentSelection = this.dependencies.selection.setSelection({
                        anchorNode,
                        anchorOffset,
                        focusNode,
                        focusOffset,
                    });
                    this.dependencies.builderOptions.updateContainers(
                        closestElement(currentSelection.commonAncestorContainer)
                    );
                    this.selectionCorrected = true;
                    break;
                } else {
                    break;
                }
            } else {
                temperaryFocusNode = node;
            }
        }
        this.dependencies.builderOptions.updateContainers(
            closestElement(selection.commonAncestorContainer)
        );
        this.selectionCorrected = true;
    }
}
