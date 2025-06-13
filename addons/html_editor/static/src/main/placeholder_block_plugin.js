import { BASE_CONTAINER_CLASS } from "@html_editor/utils/base_container";
import { Plugin } from "../plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { xml } from "@odoo/owl";
import { renderToElement } from "@web/core/utils/render";

const PLACEHOLDER_CLASS_PREFIX = "o-placeholder-block";
const BLOCK_CLASSES = Object.fromEntries(
    ["top", "bottom"].map((side) => [side, `${PLACEHOLDER_CLASS_PREFIX}-${side}`])
);
const BLOCK_SELECTORS = Object.values(BLOCK_CLASSES).map((cls) => `.${cls}`);
const CONTAINER_CLASS = `${PLACEHOLDER_CLASS_PREFIX}-container`;
const CONTAINER_SELECTOR = `.${CONTAINER_CLASS}`;
const isPartOfPlaceholderBlock = (node) => closestElement(node, CONTAINER_SELECTOR) || false;

export class PlaceholderBlockPlugin extends Plugin {
    static id = "placeholderBlock";
    static dependencies = ["baseContainer", "selection", "history"];
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: this.resetPlaceholderBlockContainers.bind(this),
        step_added_handlers: this.resetPlaceholderBlockContainers.bind(this),
        selectionchange_handlers: this.onSelectionChange.bind(this),
        unremovable_node_predicates: isPartOfPlaceholderBlock,
        unsplittable_node_predicates: isPartOfPlaceholderBlock,
        ignored_mutation_record_predicates: (record) => {
            // Ignore the insertion/removal of placeholder blocks.
            const node = record.addedNodes?.[0] || record.removedNodes?.[0];
            return node && isPartOfPlaceholderBlock(node);
        },
        move_node_blacklist_selectors: [CONTAINER_SELECTOR, ...BLOCK_SELECTORS],
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
            }
        }
    }

    onSelectionChange(selectionData) {
        const anchor = closestElement(selectionData.editableSelection.anchorNode);
        if (anchor?.matches(BLOCK_SELECTORS.join(","))) {
            // Persist the block.
            const cursors = this.dependencies.selection.preserveSelection();
            anchor.classList.remove(...Object.values(BLOCK_CLASSES));
            anchor.removeAttribute("contenteditable");
            anchor.parentElement[anchor === this.containerTop ? "after" : "before"](anchor);
            cursors.restore();
            this.resetPlaceholderBlockContainers();
            this.dependencies.history.addStep();
        }
    }
}
