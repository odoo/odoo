import { Plugin } from "@html_editor/plugin";
import { closest } from "@web/core/utils/ui";

export class DropZonePlugin extends Plugin {
    static name = "dropzone";
    static dependencies = ["history"];
    static shared = ["displayDropZone", "dropElement"];

    displayDropZone(selector) {
        this.clearDropZone();
        this.historySavePointRestore = this.shared.makeSavePoint();
        const targets = this.editable.querySelectorAll(selector);

        const createDropZone = () => {
            const dropZone = this.document.createElement("div");
            dropZone.className = "bg-info w-100 pt-3 o-dropzone";
            this.dropZoneElements.push(dropZone);
            return dropZone;
        };

        for (const target of targets) {
            if (!target.nextElementSibling?.classList.contains("o-dropzone")) {
                target.after(createDropZone());
            }

            if (!target.previousElementSibling?.classList.contains("o-dropzone")) {
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

    dropElement(elementToAdd, position) {
        const dropZone = closest(this.dropZoneElements, position);

        let target = dropZone.previousSibling;
        let addAfter = true;
        if (!target) {
            addAfter = false;
            target = dropZone.nextSibling;
        }
        this.clearDropZone();
        addAfter ? target.after(elementToAdd) : target.before(elementToAdd);
    }
}
