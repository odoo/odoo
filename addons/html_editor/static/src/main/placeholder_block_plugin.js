import { Plugin } from "../plugin";
import { fillEmpty } from "@html_editor/utils/dom";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";

// TODO: rename
export class PlaceholderBlockPlugin extends Plugin {
    static id = "placeholderBlock";
    static dependencies = ["baseContainer", "selection", "powerButtons"];
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: this.onNormalize.bind(this),
        selectionchange_handlers: this.onSelectionChange.bind(this),
        hint_targets_providers: (selectionData) => {
            const anchor = closestElement(selectionData.editableSelection.anchorNode);
            if (this.isPlaceholderBlock(anchor)) {
                return [anchor];
            } else {
                return [];
            }
        },

        move_node_blacklist_selectors: [".o-placeholder-block-container", ".o-placeholder-block"],
    };

    setup() {
        super.setup();
        this.baseContainerNodeName = this.dependencies.baseContainer.getDefaultNodeName();
        // this.baseContainerSelector =
        // getBaseContainerSelector(this.baseContainerNodeName);
        this.baseContainerSelector = this.baseContainerNodeName + ",P"; // todo: use above code instead?

        // Create the parent divs and populate them if needed.
        this.updatePlaceholderBlockContainers();
    }

    cleanForSave() {
        // this.containerTop?.remove();
        // this.containerBottom?.remove();
    }

    updatePlaceholderBlockContainers() {
        const classes = this.dependencies.baseContainer.createBaseContainer().classList;
        this.containerTop = this.editable.firstElementChild;
        if (this.isPlaceholderBlockContainer(this.containerTop)) {
            [...this.containerTop.children].forEach((child) => {
                child.classList.add("o-placeholder-block", "o-placeholder-block-top", ...classes);
                child.setAttribute("contenteditable", "true");
            });
        } else {
            this.containerTop = this.document.createElement("div");
            this.containerTop.classList.add("o-placeholder-block-container");
            this.containerTop.setAttribute("contenteditable", "false");
            this.editable.prepend(this.containerTop);
        }
        this.containerBottom = this.editable.lastElementChild;
        if (this.isPlaceholderBlockContainer(this.containerBottom)) {
            [...this.containerBottom.children].forEach((child) => {
                child.classList.add(
                    "o-placeholder-block",
                    "o-placeholder-block-bottom",
                    ...classes
                );
                child.setAttribute("contenteditable", "true");
            });
        } else {
            this.containerBottom = this.document.createElement("div");
            this.containerBottom.classList.add("o-placeholder-block-container");
            this.containerBottom.setAttribute("contenteditable", "false");
            this.editable.append(this.containerBottom);
        }
    }

    onNormalize() {
        this.updatePlaceholderBlockContainers();
        if (!this.containerTop.children.length) {
            this.containerTop.setAttribute("contenteditable", "true");
            this.containerTop.append(this.createPlaceholderBlock("top"));
            this.containerTop.setAttribute("contenteditable", "false");
        }
        if (!this.containerBottom.children.length) {
            this.containerBottom.setAttribute("contenteditable", "true");
            this.containerBottom.append(this.createPlaceholderBlock("bottom"));
            this.containerBottom.setAttribute("contenteditable", "false");
        }
    }

    /**
     * @param {"top"|"bottom"} side
     */
    createPlaceholderBlock(side) {
        const placeholderBlock = this.dependencies.baseContainer.createBaseContainer();
        placeholderBlock.classList.add("o-placeholder-block", `o-placeholder-block-${side}`);
        placeholderBlock.setAttribute("contenteditable", "true");
        fillEmpty(placeholderBlock);
        return placeholderBlock;
    }

    onSelectionChange(selectionData) {
        const anchor = closestElement(selectionData.editableSelection.anchorNode);
        if (this.isPlaceholderBlock(anchor)) {
            if (isEmptyBlock(anchor) && anchor.matches(this.baseContainerSelector)) {
                // Select the block.
                anchor.classList.add("o-placeholder-block-selected");
                this.dependencies.powerButtons.setPowerButtonsPosition(
                    anchor,
                    anchor.getBoundingClientRect(),
                    closestElement(anchor, "[dir]")?.getAttribute("dir")
                );
            } else {
                // Persist the block (if it changed).
                anchor.classList.remove(
                    "o-placeholder-block",
                    "o-placeholder-block-selected",
                    "o-placeholder-block-top",
                    "o-placeholder-block-bottom"
                );
                anchor.removeAttribute("contenteditable");
                const cursors = this.dependencies.selection.preserveSelection();
                anchor.parentElement.after(anchor);
                cursors.restore();
            }
        } else {
            // Unselect any block.
            this.editable
                .querySelectorAll(".o-placeholder-block-selected")
                .forEach((block) => block.classList.remove("o-placeholder-block-selected"));
        }
    }

    isPlaceholderBlockContainer(element) {
        return element?.matches?.(".o-placeholder-block-container") || false;
    }

    isPlaceholderBlock(element) {
        return element?.matches?.(".o-placeholder-block") || false;
    }
}
