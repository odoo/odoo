import { BASE_CONTAINER_CLASS } from "@html_editor/utils/base_container";
import { Plugin } from "../plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { xml } from "@odoo/owl";
import { renderToElement } from "@web/core/utils/render";
import { nodeSize } from "@html_editor/utils/position";

const PLACEHOLDER_CLASS_PREFIX = "o-placeholder-block";
const BLOCK_CLASSES = Object.fromEntries(
    ["top", "bottom"].map((side) => [side, `${PLACEHOLDER_CLASS_PREFIX}-${side}`])
);
const CONTAINER_CLASS = `${PLACEHOLDER_CLASS_PREFIX}-container`;
const CONTAINER_SELECTOR = `.${CONTAINER_CLASS}`;
const PLACEHOLDER_SELECTORS = [
    CONTAINER_SELECTOR,
    ...Object.values(BLOCK_CLASSES).map((cls) => `.${cls}`),
];
const isPartOfPlaceholderBlock = (node) => closestElement(node, CONTAINER_SELECTOR) || false;

export class PlaceholderBlockPlugin extends Plugin {
    static id = "placeholderBlock";
    static dependencies = ["baseContainer", "selection", "history"];
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        step_added_handlers: this.resetPlaceholderBlockContainers.bind(this),
        selectionchange_handlers: this.onSelectionChange.bind(this),
        unremovable_node_predicates: isPartOfPlaceholderBlock,
        unsplittable_node_predicates: isPartOfPlaceholderBlock,
        ignored_mutation_record_predicates: (record) => {
            // Ignore the insertion/removal of placeholder blocks.
            const node = record.addedNodes?.[0] || record.removedNodes?.[0];
            return node && isPartOfPlaceholderBlock(node);
        },
        move_node_blacklist_selectors: PLACEHOLDER_SELECTORS,
        system_classes: [CONTAINER_CLASS, ...Object.values(BLOCK_CLASSES)],
    };

    setup() {
        super.setup();
        const nodeName = this.dependencies.baseContainer.getDefaultNodeName().toLowerCase();
        const baseClass = nodeName === "P" ? "" : BASE_CONTAINER_CLASS;
        this.templates = Object.fromEntries(
            ["top", "bottom"].map((side) => [
                side,
                xml`<div class="${CONTAINER_CLASS}" contenteditable="false">
                <${nodeName} class="${BLOCK_CLASSES[side]} ${baseClass}" contenteditable="true">
                    <br/>
                </${nodeName}>
            </div>`,
            ])
        );
        this.resetPlaceholderBlockContainers();
    }

    cleanForSave({ root }) {
        root.querySelectorAll(CONTAINER_SELECTOR).forEach((block) => block.remove());
    }

    resetPlaceholderBlockContainers() {
        const selectionData = this.dependencies.selection.getSelectionData();
        const selection = selectionData.editableSelection;
        const newOffsets = { anchor: selection.anchorOffset, focus: selection.focusOffset };
        const editableSize = nodeSize(this.editable);
        for (const [side, containerName, edgeElementName, insertFunctionName] of [
            ["top", "containerTop", "firstElementChild", "prepend"],
            ["bottom", "containerBottom", "lastElementChild", "append"],
        ]) {
            this[containerName]?.remove();
            const edgeElement = this.editable[edgeElementName];
            this[containerName] = undefined;
            if (
                edgeElement?.getAttribute("contenteditable") === "false" ||
                edgeElement?.nodeName === "TABLE"
            ) {
                const container = renderToElement(this.templates[side]);
                this.editable[insertFunctionName](container);
                this[containerName] = container;
                const limit = side === "top" ? 0 : editableSize;
                for (const name of ["anchor", "focus"]) {
                    if (selection[name + "Node"] === this.editable && newOffsets[name] === limit) {
                        newOffsets[name] += side === "top" ? 1 : -1;
                    }
                }
            }
        }
        if (
            selectionData.documentSelectionIsInEditable &&
            (newOffsets.anchor !== selection.anchorOffset ||
                newOffsets.focus !== selection.focusOffset)
        ) {
            this.dependencies.selection.setSelection({
                anchorNode: selection.anchorNode,
                anchorOffset: newOffsets.anchor,
                focusNode: selection.focusNode,
                focusOffset: newOffsets.focus,
            });
        }
    }

    onSelectionChange(selectionData) {
        const anchor = closestElement(selectionData.editableSelection.anchorNode);
        if (
            selectionData.editableSelection.isCollapsed &&
            anchor?.matches(PLACEHOLDER_SELECTORS.join(","))
        ) {
            // Persist the block.
            const block = anchor.classList.contains(CONTAINER_CLASS)
                ? anchor.querySelector(PLACEHOLDER_SELECTORS)
                : anchor;
            const container = block.parentElement;
            block.classList.remove(...Object.values(BLOCK_CLASSES));
            block.removeAttribute("contenteditable");
            container[container === this.containerTop ? "after" : "before"](block);
            this.dependencies.history.addStep();
            this.dependencies.selection.setCursorEnd(block);
        }
    }
}
