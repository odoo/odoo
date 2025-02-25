import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { applyModifications, loadImageInfo } from "@html_editor/utils/image_processing";
import { _t } from "@web/core/l10n/translation";

class ImageGalleryOption extends Plugin {
    static id = "imageGalleryOption";
    static dependencies = ["media", "dom", "history", "operation"];
    resources = {
        builder_options: [
            {
                template: "html_builder.ImageGalleryOption",
                selector: ".s_image_gallery",
            },
        ],
        builder_actions: this.getActions(),
        system_classes: ["o_empty_gallery_alert"],
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: this.updateAlertBanner.bind(this),
    };

    getActions() {
        return {
            addImage: this.addImageAction,
            removeAllImages: {
                apply: ({ editingElement }) => {
                    this.insertEmptyGalleryAlert(this.getContainer(editingElement));
                },
            },
            setImageGalleryLayout: {
                load: ({ editingElement }) => this.processImages(editingElement),
                apply: ({ editingElement, param: mode, loadResult: images }) => {
                    if (mode !== this.getMode(editingElement)) {
                        this.setImages(editingElement, mode, images);
                    }
                },
                isApplied: ({ editingElement, param }) => param === this.getMode(editingElement),
            },
        };
    }

    cleanForSave({ root }) {
        for (const emptyGalleryAlert of root.querySelectorAll(".o_empty_gallery_alert")) {
            emptyGalleryAlert.remove();
        }
    }

    updateAlertBanner() {
        const imageGalleries = this.document.querySelectorAll(".s_image_gallery");
        for (const imageGallery of imageGalleries) {
            const container = this.getContainer(imageGallery);
            if (!container.querySelector("img") && !container.querySelector(".alert")) {
                this.insertEmptyGalleryAlert(container);
            }
        }
    }

    get addImageAction() {
        return {
            load: async ({ editingElement }) => {
                let selectedImages;
                await new Promise((resolve) => {
                    const onClose = this.dependencies.media.openMediaDialog({
                        onlyImages: true,
                        multiImages: true,
                        save: (images) => {
                            selectedImages = images;
                            resolve();
                        },
                    });
                    onClose.then(resolve);
                });
                if (!selectedImages) {
                    return [];
                }
                return this.processImages(editingElement, selectedImages);
            },
            apply: ({ editingElement, loadResult: images }) => {
                if (images.length) {
                    const mode = this.getMode(editingElement);
                    this.setImages(editingElement, mode, images);
                }
            },
        };
    }

    insertEmptyGalleryAlert(container) {
        const addImg = document.createElement("div");
        addImg.classList.add(
            "alert",
            "alert-info",
            "o_empty_gallery_alert",
            "text-center",
            "o_not_editable"
        );
        addImg.contentEditable = false;
        const text = document.createElement("span");
        text.classList.add("o_add_images");
        text.textContent = _t(" Add Images");
        text.style.cursor = "pointer";

        const icon = document.createElement("i");
        icon.classList.add("fa", "fa-plus-circle");

        addImg.appendChild(icon);
        addImg.appendChild(text);
        container.replaceChildren(addImg);

        this.addDomListener(addImg, "click", ({ target }) => {
            const editingElement = target.closest(".s_image_gallery");
            const applySpec = { editingElement };
            this.dependencies.operation.next(
                () => {
                    this.addImageAction.apply(applySpec);
                    this.dependencies.history.addStep();
                },
                {
                    load: async () => {
                        const loadResult = await this.addImageAction.load({ editingElement });
                        applySpec.loadResult = loadResult;
                    },
                }
            );
        });
    }

    /**
     * Set the images in the gallery by following the wanted layout
     * @param {Element} imageGalleryElement
     * @param {String('slideshow'|'masonry'|'grid'|'nomode')} mode
     * @param {Element[]} images
     */
    async setImages(imageGalleryElement, mode, images) {
        if (mode !== this.getMode(imageGalleryElement)) {
            imageGalleryElement.classList.remove("o_nomode", "o_masonry", "o_grid", "o_slideshow");
            imageGalleryElement.classList.add(`o_${mode}`);
        }
        //TODO: apply other layouts
        switch (mode) {
            case "masonry":
                this.masonry(imageGalleryElement, images);
                break;
            case "grid":
                this.grid(imageGalleryElement, images);
                break;
        }
    }

    /**
     * @param {Element} imageGalleryElement
     * @param {Element[]} images
     */
    masonry(imageGalleryElement, images) {
        const columnsNumber = this.getColumns(imageGalleryElement);
        const colClass = "col-lg-" + 12 / columnsNumber;
        const columns = [];

        const row = document.createElement("div");
        row.classList.add("row", "s_nb_column_fixed");
        this.getContainer(imageGalleryElement).replaceChildren(row);

        for (let i = 0; i < columnsNumber; i++) {
            const column = document.createElement("div");
            column.classList.add("o_masonry_col", "o_snippet_not_selectable", colClass);
            row.append(column);
            columns.push(column);
        }

        // Dispatch images in columns by always putting the next one in the smallest height column
        for (const imageEl of images) {
            let min = Infinity;
            let smallestColEl;
            for (const colEl of columns) {
                const imagesInCol = colEl.querySelectorAll("img");
                const lastImageRect =
                    imagesInCol.length &&
                    imagesInCol[imagesInCol.length - 1].getBoundingClientRect();
                const height = lastImageRect
                    ? Math.round(lastImageRect.top + lastImageRect.height)
                    : 0;
                if (height < min) {
                    min = height;
                    smallestColEl = colEl;
                }
            }
            smallestColEl.append(imageEl);
        }
    }

    /**
     * Displays the images with the "grid" layout.
     *
     * @param {Element} imageGalleryElement
     * @param {Element[]} images
     */
    grid(imageGalleryElement, images) {
        const columnsNumber = this.getColumns(imageGalleryElement);
        const colClass = "col-lg-" + 12 / columnsNumber;

        const container = this.getContainer(imageGalleryElement);
        let row = document.createElement("div");
        row.classList.add("row", "s_nb_column_fixed");
        container.replaceChildren(row);

        for (const [index, img] of images.entries()) {
            const col = this.document.createElement("div");
            col.classList.add(colClass);
            col.appendChild(img);
            row.appendChild(col);
            if ((index + 1) % columnsNumber === 0) {
                row = document.createElement("div");
                row.classList.add("row", "s_nb_column_fixed");
                container.appendChild(row);
            }
        }
    }

    async processImages(editingElement, newImages = []) {
        await this.transformImagesToWebp(newImages);
        this.setImageProperties(editingElement, newImages);
        const clonedContainerImg = await this.cloneContainerImages(editingElement);
        return [...clonedContainerImg, ...newImages];
    }

    setImageProperties(imageGalleryElement, images) {
        const lastImage = this.getImages(imageGalleryElement).at(-1);
        let lastIndex = lastImage ? this.getIndex(lastImage) : -1;
        for (const image of images) {
            image.classList.add(
                "d-block",
                "mh-100",
                "mw-100",
                "mx-auto",
                "rounded",
                "object-fit-cover"
            );
            image.dataset.index = ++lastIndex;
        }
    }

    async transformImagesToWebp(images) {
        const imagePromises = [];
        for (const imgEl of images) {
            imagePromises.push(
                new Promise((resolve) => {
                    loadImageInfo(imgEl).then(() => {
                        if (
                            imgEl.dataset.mimetype &&
                            !["image/gif", "image/svg+xml", "image/webp"].includes(
                                imgEl.dataset.mimetype
                            )
                        ) {
                            // Convert to webp but keep original width.
                            imgEl.dataset.mimetype = "image/webp";
                            applyModifications(imgEl, {
                                mimetype: "image/webp",
                            }).then((src) => {
                                imgEl.src = src;
                                imgEl.classList.add("o_modified_image_to_save");
                                resolve();
                            });
                        } else {
                            resolve();
                        }
                    });
                })
            );
        }
        return Promise.all(imagePromises);
    }

    async cloneContainerImages(imageGalleryElement) {
        const imagesHolder = this.getImageHolder(imageGalleryElement);
        const newImgs = [];
        const imgLoaded = [];
        for (const image of imagesHolder) {
            // Only on Chrome: appended images are sometimes invisible
            // and not correctly loaded from cache, we use a clone of the
            // image to force the loading.
            const newImg = image.cloneNode(true);
            newImg.loading = "eager";
            imgLoaded.push(
                newImg.decode().then(() => {
                    newImg.loading = "lazy";
                })
            );
            newImgs.push(newImg);
        }
        await Promise.all(imgLoaded);
        return newImgs;
    }

    /**
     * Get the image target's layout mode (slideshow, masonry, grid or nomode).
     *
     * @returns {String('slideshow'|'masonry'|'grid'|'nomode')}
     */
    getMode(imageGalleryElement) {
        if (imageGalleryElement.classList.contains("o_masonry")) {
            return "masonry";
        }
        if (imageGalleryElement.classList.contains("o_grid")) {
            return "grid";
        }
        if (imageGalleryElement.classList.contains("o_nomode")) {
            return "nomode";
        }
        return "slideshow";
    }

    getImages(currentContainer) {
        const imgs = currentContainer.querySelectorAll("img");
        return [...imgs].sort((imgA, imgB) => this.getIndex(imgA) - this.getIndex(imgB));
    }

    getIndex(img) {
        return parseInt(img.dataset.index) || 0;
    }

    getImageHolder(currentContainer) {
        const images = this.getImages(currentContainer);
        return [...images].map((image) => image.closest("a") || image);
    }

    getColumns(imageGalleryElement) {
        return parseInt(imageGalleryElement.dataset.columns) || 3;
    }

    getContainer(imageGalleryElement) {
        return imageGalleryElement.querySelector(
            ".container, .container-fluid, .o_container_small"
        );
    }
}

registry.category("website-plugins").add(ImageGalleryOption.id, ImageGalleryOption);
