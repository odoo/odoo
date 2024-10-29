import { Plugin } from "@html_editor/plugin";
import { closest, touching } from "@web/core/utils/ui";

export class DropZonePlugin extends Plugin {
    static name = "dropzone";
    static dependencies = ["history"];
    static shared = ["displayDropZone", "dropElement", "dragElement"];

    displayDropZone(selector) {
        this.clearDropZone();
        this.historySavePointRestore = this.shared.makeSavePoint();
        const targets = this.editable.querySelectorAll(selector);

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
        this.dropZoneElements = [];
        if (this.historySavePointRestore) {
            this.historySavePointRestore();
            this.historySavePointRestore = undefined;
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

    dropElement(elementToAdd, position) {
        const dropZone = closest(touching(this.dropZoneElements, position), position);
        if (!dropZone) {
            this.clearDropZone();
            return;
        }

        let target = dropZone.previousSibling;
        let addAfter = true;
        if (!target) {
            addAfter = false;
            target = dropZone.nextSibling;
        }
        this.clearDropZone();
        addAfter ? target.after(elementToAdd) : target.before(elementToAdd);
        this.dispatch("ADD_STEP");
    }
}
