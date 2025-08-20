import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { getDeepestPosition } from "@html_editor/utils/dom_info";
import { DIRECTIONS, nodeSize } from "@html_editor/utils/position";

export class BuilderContainerEditablePlugin extends Plugin {
    static id = "builderContainerEditable";
    static dependencies = ["history", "selection"];

    resources = {
        change_current_options_containers_listeners: this.getRestrictEditableArea.bind(this),
    };

    setup() {
        this.restrictedElement = undefined;
        this.addDomListener(this.editable, "keydown", (ev) => {
            if (getActiveHotkey(ev) === "control+a" && this.restrictedElement) {
                ev.preventDefault();
                this.selectAllInElement(this.restrictedElement);
                ev.stopPropagation();
            }
        });
        this.addDomListener(this.editable, "mouseup", this.restrictSelectionInContainer);
        this.addDomListener(this.editable, "touchend", this.restrictSelectionInContainer);
        // this.addDomListener(this.editable, "keydown", (ev) => {
        //     if (ev.key?.startsWith("Arrow")) {
        //         this.restrictSelectionInContainer();
        //     }
        // });
    }

    selectAllInElement(element) {
        const [anchorNode, anchorOffset] = getDeepestPosition(element, 0);
        const [focusNode, focusOffset] = getDeepestPosition(element, nodeSize(element));
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
        });
    }

    restrictSelectionInContainer() {
        if (!this.restrictedElement) {
            return;
        }

        const selection = this.dependencies.selection.getEditableSelection();
        if (selection.isCollapsed) {
            return;
        }

        const { anchorNode, focusNode } = selection;
        const isAnchorInRestrictedElement = this.restrictedElement.contains(anchorNode);
        const isFocusInRestrictedElement = this.restrictedElement.contains(focusNode);

        if (!isAnchorInRestrictedElement && !isFocusInRestrictedElement) {
            // if the selection is beyond the restricted element,
            // we select the whole restricted element instead
            if (this.dependencies.selection.areNodeContentsFullySelected(this.restrictedElement)) {
                this.selectAllInElement(this.restrictedElement);
            }
        } else if (isAnchorInRestrictedElement && !isFocusInRestrictedElement) {
            // if the anchor node is in the restricted element but not the focus node,
            // we adjust the focus to the end of the restricted element
            let focusNode, focusOffset;
            if (selection.direction === DIRECTIONS.RIGHT) {
                [focusNode, focusOffset] = getDeepestPosition(
                    this.restrictedElement,
                    nodeSize(this.restrictedElement)
                );
            } else {
                [focusNode, focusOffset] = getDeepestPosition(this.restrictedElement, 0);
            }
            this.dependencies.selection.setSelection({
                anchorNode,
                anchorOffset: selection.anchorOffset,
                focusNode,
                focusOffset,
            });
        } else if (!isAnchorInRestrictedElement && isFocusInRestrictedElement) {
            // if the focus node is in the restricted element but not the anchor node,
            // we adjust the anchor to the start of the restricted element
            let anchorNode, anchorOffset;
            if (selection.direction === DIRECTIONS.RIGHT) {
                [anchorNode, anchorOffset] = getDeepestPosition(this.restrictedElement, 0);
            } else {
                [anchorNode, anchorOffset] = getDeepestPosition(
                    this.restrictedElement,
                    nodeSize(this.restrictedElement)
                );
            }
            this.dependencies.selection.setSelection({
                anchorNode,
                anchorOffset,
                focusNode,
                focusOffset: selection.focusOffset,
            });
        }
    }

    getRestrictEditableArea(optionsContainer) {
        this.restrictedElement = undefined;

        // if there is only one or 0 option container, we do not restrict the selection
        // as it is the only one option container in the editable area or a blank editable area
        if (optionsContainer.length <= 1) {
            return;
        }

        const mostInnerContainerParentEl = optionsContainer.at(-1).element?.parentElement;
        const mostInnerContainerEl = optionsContainer.at(-1).element;

        if (!mostInnerContainerParentEl) {
            return;
        }
        // if the most inner container is not contenteditable, we do not restrict it
        // as it is not editable by the user
        if (mostInnerContainerEl && !mostInnerContainerEl.isContentEditable) {
            return;
        }

        this.restrictedElement = mostInnerContainerEl;
    }
}

registry
    .category("website-plugins")
    .add(BuilderContainerEditablePlugin.id, BuilderContainerEditablePlugin);
