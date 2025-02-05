import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { _t } from "@web/core/l10n/translation";
import { closest, touching } from "@web/core/utils/ui";

function filterFunction(el, exclude) {
    // TODO add all filter like website
    if (exclude && el.matches(exclude)) {
        return false;
    }
    return true;
}

/**
 * Ensures that `element` will be visible in its `scrollable`.
 *
 * @param {HTMLElement} element
 * @param {object} options
 * @param {string} [options.behavior] "smooth", "instant", "auto" <=> undefined
 *        @url https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollTo#behavior
 * @param {number} [options.offset] applies a vertical offset
 */
export function scrollToWindow(element, { behavior, offset } = {}) {
    const window = element.ownerDocument.defaultView;
    const top = element.getBoundingClientRect().top + window.scrollY - offset;

    const prom = new Promise((resolve) => {
        window.addEventListener("scrollend", () => resolve(), { once: true });
    });
    window.scrollTo({ top, behavior });
    return prom;
}

export class DropZonePlugin extends Plugin {
    static id = "dropzone";
    static dependencies = ["history"];
    static shared = ["displayDropZone", "dragElement", "clearDropZone", "getAddElement"];

    // Elements in which the initial dropzone can appear.
    static editableContentsSelector = '.oe_structure.oe_empty, [data-oe-type="html"]';

    resources = {
        savable_mutation_record_predicates: this.isMutationRecordSavable.bind(this),
        normalize_handlers: this.updateEmptyDropZone.bind(this),
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

    isDroppable(el, { selector, exclude }) {
        return el.matches(selector) && filterFunction(el, exclude);
    }

    getAll(selector) {
        return [...this.editable.querySelectorAll(selector)].filter((el) => filterFunction(el));
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

    /**
     * Return the element(s) where the initial area to drag & drop snippets
     * should appear.
     */
    get editableContentEls() {
        return Array.from(
            this.editable.querySelectorAll(this.constructor.editableContentsSelector)
        ).filter((el) => {
            const parent = el.closest(".o_editable, .o_not_editable");
            return !parent || parent.classList.contains("o_editable");
        });
    }

    /**
     * Return the initial drop zone(s) which show a message to start dropping
     * snippets.
     */
    get emptyDropZoneEls() {
        return this.editableContentEls
            .map((el) => el.querySelector(".oe_drop_zone.oe_insert[data-editor-message]"))
            .filter((el) => el);
    }

    createDropZone() {
        const dropZone = this.document.createElement("div");
        dropZone.className = "oe_drop_zone oe_insert";
        this.dropZoneElements.push(dropZone);
        return dropZone;
    }

    displayDropZone(snippet) {
        this.clearDropZone();

        // TODO need to imp check old website
        const { selectorChildren, selectorSiblings } = this.getSelectors(snippet);
        const targets = [];
        for (const el of selectorChildren) {
            targets.push(...el.children);
        }
        targets.push(...selectorSiblings);

        if (this.emptyDropZoneEls.length) {
            return;
        }
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
        this.updateEmptyDropZone();
    }

    updateEmptyDropZone() {
        const emptyEditableContentEls = this.editableContentEls.filter((el) =>
            el.matches(":empty")
        );
        if (emptyEditableContentEls.length) {
            emptyEditableContentEls.forEach((el) => {
                const emptyDropZoneEl = this.createDropZone();
                emptyDropZoneEl.dataset.editorMessage = _t("DRAG BUILDING BLOCKS HERE");
                el.appendChild(emptyDropZoneEl);
            });
        } else {
            this.emptyDropZoneEls.forEach((el) => el.remove());
        }
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
        const cancel = () => {
            this.clearDropZone();
            return () => {};
        };
        // Drag & drop over sidebar: cancel the action.
        if (position && !touching([this.document.body], position).length) {
            // TODO: do we want that key with an empty function? Or should we
            // check everytime we call getAddElement if the result is undefined
            // before continuing?
            cancel.noDrop = true;
            return cancel;
        }
        const dropZone = position
            ? closest(touching(this.dropZoneElements, position), position) ||
              closest(this.dropZoneElements, position)
            : closest(this.dropZoneElements, {
                  x: window.innerWidth / 2,
                  y: window.innerHeight / 2,
              });
        if (!dropZone) {
            return cancel();
        }

        let target, insertMethod;
        if (this.emptyDropZoneEls.includes(dropZone)) {
            insertMethod = "appendChild";
            target = dropZone.parentElement;
        }
        if (!target) {
            insertMethod = "after";
            target = dropZone.previousSibling;
        }
        if (!target) {
            insertMethod = "before";
            target = dropZone.nextSibling;
        }
        this.clearDropZone();
        return (elementToAdd) => {
            target[insertMethod](elementToAdd);
            scrollToWindow(elementToAdd, { behavior: "smooth", offset: 50 });
            this.dependencies.history.addStep();
        };
    }
}
