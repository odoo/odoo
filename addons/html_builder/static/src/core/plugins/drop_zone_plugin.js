import { scrollToWindow } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { _t } from "@web/core/l10n/translation";
import { closest, touching } from "@web/core/utils/ui";

export class DropZonePlugin extends Plugin {
    static id = "dropzone";
    static dependencies = ["history"];
    static shared = ["displayDropZone", "dragElement", "clearDropZone", "getAddElement"];

    resources = {
        savable_mutation_record_predicates: this.isMutationRecordSavable.bind(this),
    };

    setup() {
        this.dropZoneElements = [];
    }

    /**
     * @param {MutationRecord} record
     * @return {boolean}
     */
    isMutationRecordSavable(record) {
        if (record.type === "childList") {
            const node = record.addedNodes[0] || record.removedNodes[0];
            if (isBlock(node) && node.classList.contains("oe_drop_zone")) {
                return false;
            }
        }
        return true;
    }

    isDroppable(el, { selector, exclude = false }) {
        return el.matches(selector) && !el.matches(exclude);
    }

    getAll(selector) {
        return [...this.editable.querySelectorAll(selector)];
    }

    getSelectors(snippet) {
        const selectorSiblings = [];
        const selectorChildren = [];

        for (const dropZoneSelector of this.getResource("dropzone_selector")) {
            const { selector, exclude, dropIn, dropNear } = dropZoneSelector;
            if (!this.isDroppable(snippet.content, { selector, exclude })) {
                continue;
            }

            if (dropNear) {
                selectorSiblings.push(...this.getAll(dropNear));
            }
            if (dropIn) {
                selectorChildren.push(...this.getAll(dropIn));
            }
        }

        return {
            selectorSiblings,
            selectorChildren,
        };
    }

    createDropZone() {
        const dropZoneEl = this.document.createElement("div");
        dropZoneEl.className = "oe_drop_zone oe_insert";
        dropZoneEl.dataset.editorMessage = _t("DRAG BUILDING BLOCKS HERE");
        this.dropZoneElements.push(dropZoneEl);
        return dropZoneEl;
    }

    displayDropZone(snippet) {
        this.clearDropZone();

        // TODO need to imp check old website
        const { selectorChildren, selectorSiblings } = this.getSelectors(snippet);
        const targets = [];
        for (const el of selectorChildren) {
            targets.push(...el.children);
            el.prepend(this.createDropZone());
        }
        targets.push(...selectorSiblings);

        for (const target of targets) {
            if (!target.nextElementSibling?.classList.contains("oe_drop_zone")) {
                target.after(this.createDropZone());
            }

            if (!target.previousElementSibling?.classList.contains("oe_drop_zone")) {
                target.before(this.createDropZone());
            }
        }
    }

    clearDropZone() {
        if (this.dropZoneElements.length) {
            for (const el of this.editable.querySelectorAll(".oe_drop_zone")) {
                el.remove();
            }
        }

        this.dropZoneElements = [];
    }

    dragElement(element) {
        const { x, y, height, width } = element.getClientRects()[0];
        const position = { x, y, height, width };
        const dropzoneEl = closest(touching(this.dropZoneElements, position), position);
        if (this.currentDropzoneEl !== dropzoneEl) {
            this.currentDropzoneEl?.classList.remove("o_dropzone_highlighted");
            this.currentDropzoneEl = dropzoneEl;
            if (dropzoneEl) {
                dropzoneEl.classList.add("o_dropzone_highlighted");
            }
        }
    }

    /**
     * @param {Object} [position] - set if drag & drop, not set if click
     * @param {Number} position.x
     * @param {Number} position.y
     * @returns {Function}
     */
    getAddElement(position) {
        // Drag & drop over sidebar: cancel the action.
        if (position && !touching([this.document.body], position).length) {
            // TODO: do we want that key with an empty function? Or should we
            // check everytime we call getAddElement if the result is undefined
            // before continuing?
            this.clearDropZone();
            return;
        }
        const dropZone = position
            ? closest(touching(this.dropZoneElements, position), position) ||
            closest(this.dropZoneElements, position)
            : closest(this.dropZoneElements, {
                x: window.innerWidth / 2,
                y: window.innerHeight / 2,
            });
        if (!dropZone) {
            this.clearDropZone();
            return;
        }

        let target = dropZone.previousSibling;
        let insertMethod = "after";
        if (!target) {
            target = dropZone.nextSibling;
            insertMethod = "before";
        }
        if (!target) {
            target = dropZone.parentElement;
            insertMethod = "appendChild";
        }
        this.clearDropZone();
        return (elementToAdd) => {
            target[insertMethod](elementToAdd);
            scrollToWindow(elementToAdd, { behavior: "smooth", offset: 50 });
            this.dependencies.history.addStep();
            this.dispatchTo("update_interactions", elementToAdd);
        };
    }
}
