import { BuilderAction } from "@html_builder/core/builder_action";
import { resizeGrid, setElementToMaxZindex } from "@html_builder/utils/grid_layout_utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class AddElementOptionPlugin extends Plugin {
    static id = "addElementOption";
    static dependencies = ["builderOptions"];
    static shared = ["addGridElement"];
    resources = {
        builder_actions: {
            AddGridElementAction,
        },
    };

    /**
     * Adds a new grid item in the grid with the given content and properties.
     *
     * @param {HTMLElement} rowEl the grid
     * @param {HTMLElement} contentEl the content to add in the column
     * @param {Number} columnSpan the grid item column span
     * @param {Number} rowSpan the grid item row span
     * @param {Array<String>} [extraClasses = []] classes to add to the grid
     *     item
     */
    addGridElement(rowEl, contentEl, columnSpan, rowSpan, extraClasses = []) {
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
        newColumnEl.classList.add("o_grid_item", ...extraClasses);
        newColumnEl.classList.add(
            `g-col-lg-${columnSpan}`,
            `col-lg-${columnSpan}`,
            `g-height-${rowSpan}`
        );
        newColumnEl.appendChild(contentEl);

        // Place the column in the grid.
        const rowStart = this.lastStartPosition[0];
        let columnStart = this.lastStartPosition[1];
        if (columnStart + columnSpan > 13) {
            columnStart = 1;
            this.lastStartPosition[1] = columnStart;
        }
        newColumnEl.style.gridArea = `
            ${rowStart} / ${columnStart} / ${rowStart + rowSpan} / ${columnStart + columnSpan}
        `;

        // Set the z-index to the maximum of the grid.
        setElementToMaxZindex(newColumnEl, rowEl);

        // Add the new column and update the grid height.
        rowEl.appendChild(newColumnEl);
        resizeGrid(rowEl);

        // Scroll to the new column if more than half of it is hidden (= out of
        // the viewport or hidden by an other element).
        const newColumnPosition = newColumnEl.getBoundingClientRect();
        const middleX = (newColumnPosition.left + newColumnPosition.right) / 2;
        const middleY = (newColumnPosition.top + newColumnPosition.bottom) / 2;
        const sameCoordinatesEl = this.document.elementFromPoint(middleX, middleY);
        if (!sameCoordinatesEl || !newColumnEl.contains(sameCoordinatesEl)) {
            newColumnEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        // Activate the new column options.
        this.dependencies.builderOptions.setNextTarget(newColumnEl);
    }
}

/**
 * Adds an image, some text or a button in the grid.
 */
export class AddGridElementAction extends BuilderAction {
    static id = "addGridElement";
    static dependencies = ["addElementOption", "media"];

    async apply({ editingElement: rowEl, params: { mainParam: elementType } }) {
        if (elementType === "image") {
            // Choose an image with the media dialog.
            let imageEl, imageLoadedPromise;
            await new Promise((resolve) => {
                const onClose = this.dependencies.media.openMediaDialog({
                    onlyImages: true,
                    noDocuments: true,
                    save: (selectedImageEl) => {
                        imageEl = selectedImageEl;
                        imageLoadedPromise = new Promise((resolve) => {
                            imageEl.addEventListener("load", () => resolve(), { once: true });
                        });
                    },
                });
                onClose.then(resolve);
            });
            if (!imageEl) {
                return;
            }
            // Wait for the image to be loaded.
            await imageLoadedPromise;
            this.dependencies.addElementOption.addGridElement(rowEl, imageEl, 6, 6, [
                "o_grid_item_image",
            ]);
        } else if (elementType === "text") {
            // Create default text content.
            const pEl = document.createElement("p");
            pEl.textContent = _t("Write something...");
            this.dependencies.addElementOption.addGridElement(rowEl, pEl, 4, 2);
        } else if (elementType === "button") {
            // Create default button.
            const aEl = document.createElement("a");
            aEl.href = "#";
            aEl.classList.add("mb-2", "btn", "btn-primary");
            aEl.textContent = _t("Button");
            this.dependencies.addElementOption.addGridElement(rowEl, aEl, 2, 1);
        }
    }
}

registry.category("website-plugins").add(AddElementOptionPlugin.id, AddElementOptionPlugin);
