import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { loadImageInfo } from "@html_editor/utils/image_processing";
import { ImageGalleryComponent } from "./image_gallery_option";
import { renderToElement } from "@web/core/utils/render";

class ImageGalleryOption extends Plugin {
    static id = "imageGalleryOption";
    static dependencies = [
        "media",
        "dom",
        "history",
        "operation",
        "selection",
        "builder-options",
        "imagePostProcess",
    ];
    resources = {
        builder_options: [
            {
                OptionComponent: ImageGalleryComponent,
                selector: ".s_image_gallery",
            },
        ],
        builder_actions: this.getActions(),
        system_classes: ["o_empty_gallery_alert"],
        on_reorder_items_handlers: this.reorderGalleryItems.bind(this),
        on_remove_handlers: this.onRemove.bind(this),
        after_remove_handlers: this.afterRemove.bind(this),
    };

    getActions() {
        return {
            addImage: this.addImageAction,
            removeAllImages: {
                apply: ({ editingElement: el }) => {
                    const containerEl = el.querySelector(
                        ".container, .container-fluid, .o_container_small"
                    );
                    for (const subEl of containerEl.querySelectorAll(
                        ":scope > *:not(.o_empty_gallery_alert)"
                    )) {
                        subEl.remove();
                    }
                },
            },
            setImageGalleryLayout: {
                load: ({ editingElement }) => this.processImages(editingElement),
                apply: ({ editingElement, param: { mainParam: mode }, loadResult }) => {
                    if (mode !== this.getMode(editingElement)) {
                        this.setImages(editingElement, mode, loadResult.images);
                        this.restoreSelection(loadResult.imageToSelect);
                    }
                },
                isApplied: ({ editingElement, param: { mainParam: mode } }) =>
                    mode === this.getMode(editingElement),
            },
            setImageGalleryColumns: {
                load: ({ editingElement }) => this.processImages(editingElement),
                apply: ({ editingElement, param: { mainParam: columns }, loadResult }) => {
                    if (columns !== this.getColumns(editingElement)) {
                        editingElement.dataset.columns = columns;
                        this.setImages(
                            editingElement,
                            this.getMode(editingElement),
                            loadResult.images
                        );
                        this.restoreSelection(loadResult.imageToSelect);
                    }
                },
                isApplied: ({ editingElement, param: { mainParam: columns } }) =>
                    columns === this.getColumns(editingElement),
            },
            setCarouselSpeed: {
                apply: ({ editingElement, value }) => {
                    editingElement.dataset.bsInterval = value * 1000;
                },
                getValue: ({ editingElement }) => editingElement.dataset.bsInterval / 1000,
            },
        };
    }

    setup() {
        const slideshowCarousels = this.document.querySelectorAll(".s_image_gallery .carousel");
        for (const carousel of slideshowCarousels) {
            this.addDomListener(carousel, "slid.bs.carousel", this.onCarouselSlid);
        }
    }
    restoreSelection(imageToSelect) {
        if (imageToSelect && !this.dependencies.history.getIsPreviewing()) {
            // We want to update the container to the equivalent cloned image.
            // This has to be done in the new step so we manually add a step
            this.dependencies.history.addStep();
            this.dependencies["builder-options"].updateContainers(imageToSelect);
        }
    }

    reorderGalleryItems({ elementToReorder, position, optionName }) {
        if (optionName === "GalleryImageList") {
            const editingGalleryElement = elementToReorder.closest(".s_image_gallery");

            const container = this.getContainer(editingGalleryElement);

            const itemsEls = this.getImages(container);
            const oldPosition = itemsEls.indexOf(elementToReorder);
            if (oldPosition === 0 && position === "prev") {
                position = "last";
            } else if (oldPosition === itemsEls.length - 1 && position === "next") {
                position = "first";
            }
            itemsEls.splice(oldPosition, 1);
            switch (position) {
                case "first":
                    itemsEls.unshift(elementToReorder);
                    break;
                case "prev":
                    itemsEls.splice(Math.max(oldPosition - 1, 0), 0, elementToReorder);
                    break;
                case "next":
                    itemsEls.splice(oldPosition + 1, 0, elementToReorder);
                    break;
                case "last":
                    itemsEls.push(elementToReorder);
                    break;
            }

            const newItemPosition = itemsEls.indexOf(elementToReorder);
            itemsEls.forEach((img, index) => {
                img.dataset.index = index;
            });
            const mode = this.getMode(editingGalleryElement);
            this.setImages(editingGalleryElement, mode, itemsEls);

            if (mode === "slideshow") {
                const carouselEl = editingGalleryElement.querySelector(".carousel");
                const carouselInstance = window.Carousel.getOrCreateInstance(carouselEl, {
                    ride: false,
                    pause: true,
                });

                carouselInstance.to(newItemPosition);
                const activeImageEl = editingGalleryElement.querySelector(
                    ".carousel-item.active img"
                );
                this.dependencies["builder-options"].updateContainers(activeImageEl);
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
            apply: ({ editingElement, loadResult: { images } }) => {
                if (images.length) {
                    const mode = this.getMode(editingElement);
                    this.setImages(editingElement, mode, images);
                }
            },
        };
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
        switch (mode) {
            case "masonry":
                this.masonry(imageGalleryElement, images);
                break;
            case "grid":
                this.grid(imageGalleryElement, images);
                break;
            case "nomode":
                this.nomode(imageGalleryElement, images);
                break;
            case "slideshow":
                this.slideshow(imageGalleryElement, images);
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

    nomode(imageGalleryElement, images) {
        const row = this.document.createElement("div");
        row.classList.add("row", "s_nb_column_fixed");
        const container = this.getContainer(imageGalleryElement);
        container.replaceChildren(row);
        for (const img of images) {
            let wrapClass = "col-lg-3";
            if (img.width >= img.height * 2 || img.width > 600) {
                wrapClass = "col-lg-6";
            }

            const wrap = this.document.createElement("div");
            wrap.classList.add(wrapClass);
            wrap.appendChild(img);
            row.appendChild(wrap);
        }
    }

    slideshow(imageGalleryElement, images) {
        const container = this.getContainer(imageGalleryElement);
        const currentInterval = imageGalleryElement.querySelector(".carousel").dataset.bsInterval;
        const carouselEl = imageGalleryElement.querySelector(".carousel");
        const colorContrast =
            carouselEl && carouselEl.classList.contains("carousel-dark") ? "carousel-dark" : " ";
        const slideshowEl = renderToElement("html_builder.s_image_gallery_slideshow", {
            images: images,
            index: 0,
            interval: currentInterval || 0,
            ride: !currentInterval ? "false" : "carousel",
            id: "slideshow_" + new Date().getTime(),
            colorContrast,
        });
        carouselEl.removeEventListener("slid.bs.carousel", this.onCarouselSlid);
        container.replaceChildren(slideshowEl);
        slideshowEl.querySelectorAll("img").forEach((img, index) => {
            img.setAttribute("data-index", index);
        });

        imageGalleryElement.style.height = window.innerHeight * 0.7 + "px";
        this.addDomListener(slideshowEl, "slid.bs.carousel", this.onCarouselSlid);
    }

    onCarouselSlid(ev) {
        // When the carousel slides, update the builder options to select the active image
        const activeImageEl = ev.target.querySelector(".carousel-item.active img");
        this.dependencies["builder-options"].updateContainers(activeImageEl);
    }

    async processImages(editingElement, newImages = []) {
        await this.transformImagesToWebp(newImages);
        this.setImageProperties(editingElement, newImages);
        const { clonedImgs, imageToSelect } = await this.cloneContainerImages(editingElement);
        return { images: [...clonedImgs, ...newImages], imageToSelect };
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
                    loadImageInfo(imgEl).then((newDataset) => {
                        Object.assign(imgEl.dataset, newDataset);
                        if (
                            imgEl.dataset.mimetype &&
                            !["image/gif", "image/svg+xml", "image/webp"].includes(
                                imgEl.dataset.mimetype
                            )
                        ) {
                            // Convert to webp but keep original width.
                            this.dependencies.imagePostProcess
                                .processImage(imgEl, {
                                    mimetype: "image/webp",
                                })
                                .then((updateImgAttributes) => {
                                    updateImgAttributes();
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
        const clonedImgs = [];
        const imgLoaded = [];
        let imageToSelect;
        const currentContainers = this.dependencies["builder-options"].getContainers();
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
            if (currentContainers.at(-1)?.element === image) {
                imageToSelect = newImg;
            }
            clonedImgs.push(newImg);
        }
        await Promise.all(imgLoaded);
        return { clonedImgs, imageToSelect };
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

    onRemove(elementToRemove) {
        // If the removed element is an image from a gallery, store the gallery element for afterRemove
        if (elementToRemove.matches(".s_image_gallery img")) {
            this.imageRemovedGalleryElement = elementToRemove.closest(".s_image_gallery");
        }
    }

    afterRemove(elementRemoved) {
        // If the removed element is an image from a gallery, relayout the gallery
        if (this.imageRemovedGalleryElement) {
            const mode = this.getMode(this.imageRemovedGalleryElement);
            const images = this.getImages(this.imageRemovedGalleryElement);
            this.setImages(this.imageRemovedGalleryElement, mode, images);
            this.imageRemovedGalleryElement = undefined;
        }
    }
}

registry.category("website-plugins").add(ImageGalleryOption.id, ImageGalleryOption);
