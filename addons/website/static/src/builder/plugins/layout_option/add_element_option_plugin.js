import { BuilderAction } from "@html_builder/core/builder_action";
import { resizeGrid, setElementToMaxZindex } from "@html_builder/utils/grid_layout_utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class AddElementOptionPlugin extends Plugin {
    static id = "addElementOption";
    static dependencies = ["history", "media"];
    static shared = ["addElement"];
    resources = {
        builder_actions: {
            AddElTextAction,
            AddElImageAction,
            AddElButtonAction,
        },
    };

    /**
     * Adds an image, some text or a button in the grid.
     *
     * It can probaly be refactored and improved.
     *
     * @see this.selectClass for parameters
     * @see based on addons/web_editor/static/src/js/editor/snippets.options.js::addElement()
     */
    addElement(container, element, colSize, rowSize, classes) {
        // If it has been less than 15 seconds that we have added an element,
        // shift the new element right and down by one cell. Otherwise, put it
        // in the top left corner.
        const currentTime = new Date().getTime();
        if (this.lastAddTime && (currentTime - this.lastAddTime) / 1000 < 15) {
            this.lastStartPosition = [this.lastStartPosition[0] + 1, this.lastStartPosition[1] + 1];
        } else {
            this.lastStartPosition = [1, 1]; // [rowStart, columnStart]
        }
        this.lastAddTime = currentTime;

        // Create the new column.
        const newColumnEl = document.createElement("div");
        newColumnEl.classList.add("o_grid_item", ...classes);
        newColumnEl.appendChild(element);

        // Place the column in the grid.
        const rowStart = this.lastStartPosition[0];
        let columnStart = this.lastStartPosition[1];
        if (columnStart + colSize > 13) {
            columnStart = 1;
            this.lastStartPosition[1] = columnStart;
        }
        newColumnEl.style.gridArea = `${rowStart} / ${columnStart} / ${rowStart + rowSize} / ${
            columnStart + colSize
        }`;

        // Setting the z-index to the maximum of the grid.
        setElementToMaxZindex(newColumnEl, container);

        // Add the new column and update the grid height.
        container.appendChild(newColumnEl);
        resizeGrid(container);

        const newColumnPosition = newColumnEl.getBoundingClientRect();
        const middleX = (newColumnPosition.left + newColumnPosition.right) / 2;
        const middleY = (newColumnPosition.top + newColumnPosition.bottom) / 2;
        const sameCoordinatesEl = this.document.elementFromPoint(middleX, middleY);
        if (!sameCoordinatesEl || !newColumnEl.contains(sameCoordinatesEl)) {
            newColumnEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        this.dependencies.history.addStep();
    }
}

export class AddElTextAction extends BuilderAction {
    static id = "addElText";
    static dependencies = ["addElementOption"];
    apply({ editingElement }) {
        const colSize = 4;
        const rowSize = 2;

        const newElement = document.createElement("p");
        newElement.textContent = _t("Write something...");

        this.dependencies.addElementOption.addElement(
            editingElement,
            newElement,
            colSize,
            rowSize,
            ["col-lg-4", "g-col-lg-4", "g-height-2"]
        );
    }
}
export class AddElImageAction extends BuilderAction {
    static id = "addElImage";
    static dependencies = ["media", "addElementOption"];
    async load({ editingElement }) {
        let selectedImage;
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                onlyImages: true,
                node: editingElement,
                save: (images) => {
                    selectedImage = images;
                    resolve();
                },
            });
            onClose.then(resolve);
        });
        if (!selectedImage) {
            return;
        }

        await new Promise((resolve) => {
            selectedImage.addEventListener("load", () => resolve(), {
                once: true,
            });
        });
        return selectedImage;
    }
    apply({ editingElement, loadResult: image }) {
        if (!image) {
            return;
        }
        const colSize = 6;
        const rowSize = 6;

        this.dependencies.addElementOption.addElement(editingElement, image, colSize, rowSize, [
            "col-lg-6",
            "g-col-lg-6",
            "g-height-6",
            "o_grid_item_image",
        ]);
    }
}
export class AddElButtonAction extends BuilderAction {
    static id = "addElButton";
    static dependencies = ["addElementOption"];
    apply({ editingElement }) {
        const colSize = 2;
        const rowSize = 1;

        const newButton = document.createElement("a");
        newButton.href = "#";
        newButton.classList.add("mb-2", "btn", "btn-primary");
        newButton.textContent = "Button";

        this.dependencies.addElementOption.addElement(editingElement, newButton, colSize, rowSize, [
            "col-lg-2",
            "g-col-lg-2",
            "g-height-1",
        ]);
    }
}

registry.category("website-plugins").add(AddElementOptionPlugin.id, AddElementOptionPlugin);
