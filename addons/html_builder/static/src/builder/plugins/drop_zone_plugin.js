import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { closest, touching } from "@web/core/utils/ui";

function computeSelector({ editable, selector, exclude }) {
    const filterFunction = (el) => {
        // TODO add all filter like website
        if (exclude && el.matches(exclude)) {
            return false;
        }
        return true;
    };
    return {
        is: (el) => el.matches(selector) && filterFunction(el),
        all: () => [...editable.querySelectorAll(selector)].filter(filterFunction),
    };
}

export class DropZonePlugin extends Plugin {
    static id = "dropzone";
    static dependencies = ["history"];
    static shared = ["displayDropZone", "dragElement", "clearDropZone", "getAddElement"];

    resources = {
        savable_mutation_record_predicates: this.isMutationRecordSavable.bind(this),
    };

    setup() {
        this.dropZoneElements = [];

        this.dropZoneSelectors = this.getResource("dropzone_selector").map(
            ({ selector, exclude, dropIn, dropNear }) => ({
                selector: computeSelector({ editable: this.editable, selector, exclude }),
                dropIn: computeSelector({ editable: this.editable, selector: dropIn, exclude }),
                dropNear: computeSelector({
                    editable: this.editable,
                    selector: dropNear,
                    exclude,
                }),
            })
        );
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

    getSelectors(snippet) {
        const selectorSiblings = [];
        const selectorChildren = [];

        for (const dropZoneSelector of this.dropZoneSelectors) {
            const { selector, dropNear, dropIn } = dropZoneSelector;
            if (!selector.is(snippet.content)) {
                continue;
            }

            if (dropNear) {
                selectorSiblings.push(...dropNear.all());
            }
            if (dropIn) {
                selectorChildren.push(...dropIn.all());
            }
        }

        return {
            selectorSiblings,
            selectorChildren,
        };
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

        const createDropZone = () => {
            const dropZone = this.document.createElement("div");
            dropZone.className = "oe_drop_zone oe_insert";
            this.dropZoneElements.push(dropZone);
            return dropZone;
        };

        for (const target of targets) {
            if (!target.nextElementSibling?.classList.contains("oe_drop_zone")) {
                target.after(createDropZone());
            }

            if (!target.previousElementSibling?.classList.contains("oe_drop_zone")) {
                target.before(createDropZone());
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

    getAddElement(position) {
        const dropZone = position
            ? closest(touching(this.dropZoneElements, position), position)
            : closest(this.dropZoneElements, {
                  x: window.innerWidth / 2,
                  y: window.innerHeight / 2,
              });
        if (!dropZone) {
            this.clearDropZone();
            return () => {};
        }
        let target = dropZone.previousSibling;
        let addAfter = true;
        if (!target) {
            addAfter = false;
            target = dropZone.nextSibling;
        }
        this.clearDropZone();
        return (elementToAdd) => {
            addAfter ? target.after(elementToAdd) : target.before(elementToAdd);
            this.dependencies.history.addStep();
        };
    }
}
