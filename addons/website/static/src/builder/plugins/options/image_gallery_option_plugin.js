import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { loadImageInfo } from "@html_editor/utils/image_processing";
import { updateCarouselIndicators } from "../carousel_option_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { hasMediaOnly, isMediaElement } from "@html_editor/utils/dom_info";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { forwardToThumbnail } from "@html_builder/utils/utils_css";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { uuid } from "@web/core/utils/strings";

/**
 * @typedef { Object } ImageGalleryOptionShared
 * @property { ImageGalleryOptionPlugin['getColumns'] } getColumns
 * @property { ImageGalleryOptionPlugin['getMode'] } getMode
 * @property { ImageGalleryOptionPlugin['processImage'] } processImage
 * @property { ImageGalleryOptionPlugin['restoreSelection'] } restoreSelection
 * @property { ImageGalleryOptionPlugin['setImages'] } setImages
 */

export class ImageGalleryOptionPlugin extends Plugin {
    static id = "imageGalleryOption";
    static dependencies = [
        "media",
        "dom",
        "history",
        "operation",
        "selection",
        "builderOptions",
        "imagePostProcess",
    ];
    static shared = ["processImages", "getMode", "setImages", "restoreSelection", "getColumns"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            AddImageAction,
            RemoveAllImagesAction,
            SetImageGalleryLayoutAction,
            SetImageGalleryColumnsAction,
            IndicatorsStyleClassAction,
        },
        system_classes: ["o_empty_gallery_alert"],
        gallery_items_providers: this.getGalleryItems.bind(this),
        reorder_items_processors: this.reorderGalleryItems.bind(this),
        on_will_remove_handlers: this.onWillRemove.bind(this),
        on_removed_handlers: this.onRemoved.bind(this),
        on_media_replaced_handlers: ({ newMediaEl }) => this.updateCarouselThumbnail(newMediaEl),
        on_image_updated_handlers: ({ imageEl }) => this.updateCarouselThumbnail(imageEl),
        on_image_saved_handlers: ({ imageEl }) => this.updateCarouselThumbnail(imageEl),
        on_snippet_dropped_handlers: ({ snippetEl }) => {
            const galleries = this.document.querySelectorAll(".s_image_gallery");
            for (const galleryEl of galleries) {
                const container = this.getContainer(galleryEl);
                const images = this.getImages(container);
                const mode = this.getMode(galleryEl);
                // Use setImages to rebuild the proper structure for the current mode.
                // For masonry this will dispatch items into columns and initialize DnD.
                this.setImages(galleryEl, mode, images);
                // Ensure carousel listeners/ids are in place when rebuilt.
                const carouselEl = galleryEl.querySelector(".carousel");
                if (carouselEl) {
                    this.addCarouselListener([carouselEl]);
                    this.addUniqueIds([carouselEl]);
                }
            }
        },
        on_cloned_handlers: ({ cloneEl }) => {
            const carousels = cloneEl.querySelectorAll(".s_image_gallery .carousel");
            this.addUniqueIds(carousels);
        },
        // Make sure s_image_gallery elements are not editable, while keeping
        // the media they contain editable (+ compatibility with older
        // versions).
        content_editable_providers: this.getContentEditableEls.bind(this),
        content_not_editable_providers: this.getContentNotEditableEls.bind(this),
        dropzone_selectors: {
            selector: ".s_image_gallery .row > div",
            dropNear: ".s_image_gallery .row > div",
            dropLockWithin: ".s_image_gallery",
        },
    };

    setup() {
        const slideshowCarousels = this.document.querySelectorAll(".s_image_gallery .carousel");
        this.addCarouselListener(slideshowCarousels);
    }

    addUniqueIds(carousels) {
        for (const carousel of carousels) {
            const id = `slideshow_${uuid()}`;
            carousel.id = id;
            const controllerButtons = carousel.querySelectorAll(".o_carousel_controllers button");
            for (const button of controllerButtons) {
                button.setAttribute("data-bs-target", `#${id}`);
            }
        }
    }

    addCarouselListener(slideshowCarousels) {
        for (const carousel of slideshowCarousels) {
            this.addDomListener(carousel, "slid.bs.carousel", this.onCarouselSlid);
        }
    }

    restoreSelection(imageToSelect, isPreviewing) {
        if (imageToSelect && !isPreviewing) {
            // Activate the containers of the equivalent cloned image.
            this.dependencies.builderOptions.setNextTarget(imageToSelect);
        }
    }

    /**
     * Gets the gallery images to reorder.
     *
     * @param {HTMLElement} activeItemEl the current active image
     * @param {String} optionName
     * @returns {Array<HTMLElement>}
     */
    getGalleryItems(activeItemEl, optionName) {
        let itemEls = [];
        if (optionName === "GalleryImageList") {
            const galleryEl = activeItemEl.closest(".s_image_gallery");
            const containerEl = this.getContainer(galleryEl);
            itemEls = this.getImageHolder(containerEl);
        }
        return itemEls;
    }

    /**
     * Updates the DOM with the reordered images.
     *
     * @param {HTMLElement} activeItemEl the active item
     * @param {Array<HTMLElement>} itemEls the reordered elements
     * @param {String} optionName
     */
    reorderGalleryItems(activeItemEl, itemEls, optionName) {
        if (optionName === "GalleryImageList") {
            const galleryEl = activeItemEl.closest(".s_image_gallery");

            // Update the content with the new order.
            itemEls.forEach((itemEl, i) => {
                const imgEl = this.getImageElement(itemEl);
                imgEl.dataset.index = i;
            });
            const mode = this.getMode(galleryEl);
            this.setImages(galleryEl, mode, itemEls);

            // Update the active slide if it is a carousel.
            if (mode === "slideshow") {
                const newPosition = itemEls.indexOf(activeItemEl);
                const carouselEl = galleryEl.querySelector(".carousel");
                const carouselItemEls = carouselEl.querySelectorAll(".carousel-item");
                carouselItemEls.forEach((itemEl, i) => {
                    itemEl.classList.toggle("active", i === newPosition);
                });
                updateCarouselIndicators(carouselEl, newPosition);

                // Activate the active image.
                const activeImageEl = galleryEl.querySelector(".carousel-item.active img");
                this.dependencies.builderOptions.setNextTarget(activeImageEl);
            }
        }
    }

    /**
     * Set the images in the gallery by following the wanted layout
     * @param {Element} imageGalleryElement
     * @param {String('slideshow'|'masonry'|'grid'|'nomode')} mode
     * @param {Element[]} images
     */
    setImages(imageGalleryElement, mode, images) {
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
            column.classList.add("o_masonry_col", colClass);
            row.append(column);
            columns.push(column);
        }

        // Unwrap images if they're already wrapped
        const unwrappedImages = images.map((img) => {
            if (
                img.parentElement &&
                img.parentElement.classList.contains("o_masonry_image_wrapper")
            ) {
                const wrapper = img.parentElement;
                const parent = wrapper.parentElement;
                if (parent) {
                    parent.insertBefore(img, wrapper);
                    wrapper.remove();
                }
            }
            return img;
        });

        // Add data-index to track order
        unwrappedImages.forEach((img, index) => {
            img.dataset.imageIndex = index;
        });

        // Dispatch images in columns by always putting the next one in the smallest height column
        for (const imageEl of unwrappedImages) {
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

        // After layout is complete, wrap images for drag and drop
        const allImages = imageGalleryElement.querySelectorAll("img");
        allImages.forEach((img) => {
            if (!img.parentElement.classList.contains("o_masonry_image_wrapper")) {
                this.createDraggableWrapper(img);
            }
        });

        // Initialize drag and drop
        this.initializeDragAndDrop(imageGalleryElement);
        this.dependencies.history.addStep();
    }

    createDraggableWrapper(imageEl) {
        const wrapper = document.createElement("div");
        wrapper.classList.add("o_masonry_image_wrapper");
        wrapper.style.position = "relative";
        wrapper.style.cursor = "move";
        wrapper.style.display = "inline-block";
        wrapper.style.width = "100%";

        // Store the image index on the wrapper too
        wrapper.dataset.imageIndex = imageEl.dataset.imageIndex;

        // Create overlay for drag handle
        const overlay = document.createElement("div");
        overlay.classList.add("o_masonry_drag_overlay");
        overlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0);
            transition: background 0.2s;
            z-index: 10;
            cursor: move;
        `;

        // Show overlay on hover
        wrapper.addEventListener("mouseenter", () => {
            overlay.style.background = "rgba(0, 0, 0, 0.3)";
        });

        wrapper.addEventListener("mouseleave", () => {
            overlay.style.background = "rgba(0, 0, 0, 0)";
        });

        // Wrap the image in place
        const parent = imageEl.parentElement;
        parent.insertBefore(wrapper, imageEl);
        wrapper.append(imageEl);
        wrapper.append(overlay);

        return wrapper;
    }

    initializeDragAndDrop(imageGalleryElement) {
        let draggedWrapper = null;

        const wrappers = imageGalleryElement.querySelectorAll(".o_masonry_image_wrapper");

        wrappers.forEach((wrapper) => {
            const overlay = wrapper.querySelector(".o_masonry_drag_overlay");
            overlay.setAttribute("draggable", "true");

            overlay.addEventListener("dragstart", (e) => {
                draggedWrapper = wrapper;
                wrapper.style.opacity = "0.5";
                e.dataTransfer.effectAllowed = "move";
                e.dataTransfer.setData("text/plain", wrapper.dataset.imageIndex);
            });

            overlay.addEventListener("dragend", (e) => {
                wrapper.style.opacity = "1";
                draggedWrapper = null;
            });

            // Allow dropping on other wrappers
            wrapper.addEventListener("dragover", (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";

                // Visual feedback - highlight the target
                if (draggedWrapper && wrapper !== draggedWrapper) {
                    wrapper.style.outline = "3px solid #007bff";
                }
            });

            wrapper.addEventListener("dragleave", (e) => {
                wrapper.style.outline = "";
            });

            wrapper.addEventListener("drop", (e) => {
                e.preventDefault();
                e.stopPropagation();
                wrapper.style.outline = "";

                if (!draggedWrapper || wrapper === draggedWrapper) {
                    return;
                }

                // Get indices
                const draggedIndex = parseInt(draggedWrapper.dataset.imageIndex);
                const targetIndex = parseInt(wrapper.dataset.imageIndex);

                console.log(`Swapping image ${draggedIndex} with image ${targetIndex}`);

                // Get all images in order by their data-index
                const allWrappers = Array.from(
                    imageGalleryElement.querySelectorAll(".o_masonry_image_wrapper")
                );

                // Sort by current index to get ordered array
                allWrappers.sort(
                    (a, b) => parseInt(a.dataset.imageIndex) - parseInt(b.dataset.imageIndex)
                );

                // Swap the two items in the array
                const draggedPos = allWrappers.findIndex(
                    (w) => parseInt(w.dataset.imageIndex) === draggedIndex
                );
                const targetPos = allWrappers.findIndex(
                    (w) => parseInt(w.dataset.imageIndex) === targetIndex
                );

                if (draggedPos !== -1 && targetPos !== -1) {
                    // Swap in array
                    [allWrappers[draggedPos], allWrappers[targetPos]] = [
                        allWrappers[targetPos],
                        allWrappers[draggedPos],
                    ];

                    // Extract images from wrappers
                    const reorderedImages = allWrappers.map((w) => {
                        const img = w.querySelector("img");
                        w.replaceChildren();
                        return img;
                    });

                    // Update indices to match new order
                    reorderedImages.forEach((img, index) => {
                        img.dataset.imageIndex = index;
                    });

                    // Rebuild masonry with swapped order
                    this.masonry(imageGalleryElement, reorderedImages);
                }
            });
        });
    }

    // Helper method to get current image order
    getImageOrder(imageGalleryElement) {
        const images = Array.from(
            imageGalleryElement.querySelectorAll(".o_masonry_image_wrapper img")
        );
        // Sort by current visual order and return indices
        return images.map((img) => parseInt(img.dataset.imageIndex));
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

    nomode(imageGalleryElement, itemEls) {
        const row = this.document.createElement("div");
        row.classList.add("row", "s_nb_column_fixed");
        const container = this.getContainer(imageGalleryElement);
        container.replaceChildren(row);
        for (const itemEl of itemEls) {
            const imgEl = this.getImageElement(itemEl);
            let wrapClass = "col-lg-3";
            if (imgEl.width >= imgEl.height * 2 || imgEl.width > 600) {
                wrapClass = "col-lg-6";
            }

            const wrap = this.document.createElement("div");
            wrap.classList.add(wrapClass);
            wrap.appendChild(itemEl);
            row.appendChild(wrap);
        }
    }

    slideshow(imageGalleryElement, itemEls) {
        const container = this.getContainer(imageGalleryElement);
        const currentInterval = imageGalleryElement.querySelector(".carousel")?.dataset.bsInterval;
        const carouselEl = imageGalleryElement.querySelector(".carousel");
        const colorContrast =
            carouselEl && carouselEl.classList.contains("carousel-dark") ? "carousel-dark" : " ";

        const imagesData = itemEls.map((itemEl) => {
            const imgEl = this.getImageElement(itemEl);
            const linkEl = itemEl.tagName === "A" ? itemEl : null;
            return { imgEl, linkEl };
        });

        const images = imagesData.map((data) => data.imgEl);
        const slideshowEl = renderToElement("website.s_image_gallery_slideshow", {
            images: images,
            index: 0,
            interval: currentInterval || 0,
            ride: !currentInterval ? "false" : "carousel",
            id: "slideshow_" + new Date().getTime(),
            colorContrast,
            copyAttributes: true,
            getIndicatorLabel: (itemPosition, total) =>
                _t("Slide %(itemPosition)s of %(total)s", { itemPosition, total }),
        });
        if (carouselEl) {
            carouselEl.removeEventListener("slid.bs.carousel", this.onCarouselSlid);
        }
        container.replaceChildren(slideshowEl);
        slideshowEl
            .querySelectorAll("img:not(.o_carousel_controllers img)")
            .forEach((img, index) => {
                img.setAttribute("data-index", index);
                if (imagesData[index]?.linkEl) {
                    const linkEl = imagesData[index].linkEl.cloneNode(false);
                    img.before(linkEl);
                    linkEl.append(img);
                }
            });
        if (images.length) {
            slideshowEl
                .querySelector(".carousel .o_carousel_controllers")
                ?.classList.remove("d-none");
            slideshowEl.querySelector(".carousel .carousel-inner")?.classList.remove("d-none");
        } else {
            imageGalleryElement.style.removeProperty("height");
            slideshowEl.querySelector(".carousel .o_carousel_controllers")?.classList.add("d-none");
            slideshowEl.querySelector(".carousel .carousel-inner")?.classList.add("d-none");
        }
        this.addDomListener(slideshowEl, "slid.bs.carousel", this.onCarouselSlid);
    }

    onCarouselSlid(ev) {
        // When the carousel slides, update the builder options to select the active image
        const activeImageEl = ev.target.querySelector(".carousel-item.active img");
        this.dependencies.builderOptions.updateContainers(activeImageEl);
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
        const process = async (img) => {
            const newDataset = await loadImageInfo(img);
            const { mimetypeBeforeConversion } = { ...img.dataset, ...newDataset };
            if (
                mimetypeBeforeConversion &&
                !["image/gif", "image/svg+xml", "image/webp"].includes(mimetypeBeforeConversion)
            ) {
                // Convert to webp but keep original width.
                const update = await this.dependencies.imagePostProcess.processImage({
                    img,
                    newDataset: {
                        formatMimetype: "image/webp",
                        ...newDataset,
                    },
                });
                update();
            }
        };
        return await Promise.all(images.map(process));
    }

    async cloneContainerImages(imageGalleryElement) {
        const imagesHolder = this.getImageHolder(imageGalleryElement);
        const clonedImgs = [];
        const imgLoaded = [];
        let imageToSelect;
        const currentContainers = this.dependencies.builderOptions.getContainers();
        for (const image of imagesHolder) {
            // Only on Chrome: appended images are sometimes invisible
            // and not correctly loaded from cache, we use a clone of the
            // image to force the loading.
            const newImg = image.cloneNode(true);
            const imgEl = newImg.tagName === "IMG" ? newImg : newImg.querySelector(":scope > img");
            imgEl.loading = "eager";
            imgLoaded.push(
                imgEl.decode().then(() => {
                    imgEl.loading = "lazy";
                })
            );
            if (currentContainers.at(-1)?.element === image) {
                imageToSelect = newImg;
            }
            clonedImgs.push(newImg);
        }
        await Promise.allSettled(imgLoaded);
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
        const imgs = currentContainer.querySelectorAll("img:not(.o_carousel_controllers img)");
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

    onWillRemove(toRemoveEl) {
        // If the removed element is an image from a gallery, store the gallery
        // element for `onRemoved`.
        if (toRemoveEl.matches(".s_image_gallery img:not(.o_carousel_controllers img)")) {
            this.imageRemovedGalleryElement = toRemoveEl.closest(".s_image_gallery");
        }
    }

    onRemoved() {
        // If the removed element is an image from a gallery, relayout the
        // gallery.
        if (this.imageRemovedGalleryElement) {
            const mode = this.getMode(this.imageRemovedGalleryElement);
            const images = this.getImageHolder(this.imageRemovedGalleryElement);
            this.setImages(this.imageRemovedGalleryElement, mode, images);
            this.imageRemovedGalleryElement = undefined;
        }
    }

    updateCarouselThumbnail(mediaEl) {
        if (mediaEl.matches(".s_image_gallery img")) {
            forwardToThumbnail(mediaEl);
        }
    }

    getImageElement(el) {
        return el.tagName === "IMG" ? el : el.querySelector("img");
    }

    getContentEditableEls(rootEl) {
        return [...selectElements(rootEl, ".s_image_gallery *")].filter(
            (el) => isMediaElement(el) || el.tagName === "IMG"
        );
    }

    getContentNotEditableEls(rootEl) {
        return [
            ...selectElements(
                rootEl,
                ".s_image_gallery .row > *, .s_image_gallery .carousel-inner > *"
            ),
        ].filter((el) => hasMediaOnly(el, !!el.closest(".o_grid, .o_nomode, .o_slideshow")));
    }
}

export class AddImageAction extends BuilderAction {
    static id = "addImage";
    static dependencies = ["media", "imageGalleryOption"];
    setup() {
        this.canTimeout = false;
    }
    async apply({ editingElement }) {
        await this.dependencies.media.openMediaDialog({
            onlyImages: true,
            multiImages: true,
            save: async (images) => {
                const { images: processedImages } =
                    await this.dependencies.imageGalleryOption.processImages(
                        editingElement,
                        images
                    );
                if (processedImages && processedImages.length) {
                    const mode = this.dependencies.imageGalleryOption.getMode(editingElement);
                    this.dependencies.imageGalleryOption.setImages(
                        editingElement,
                        mode,
                        processedImages
                    );
                }
            },
        });
    }
}
export class RemoveAllImagesAction extends BuilderAction {
    static id = "removeAllImages";
    static dependencies = ["imageGalleryOption"];
    apply({ editingElement: el }) {
        const mode = this.dependencies.imageGalleryOption.getMode(el);
        this.dependencies.imageGalleryOption.setImages(el, mode, []);
    }
}
export class SetImageGalleryLayoutAction extends BuilderAction {
    static id = "setImageGalleryLayout";
    static dependencies = ["imageGalleryOption"];
    load({ editingElement }) {
        return this.dependencies.imageGalleryOption.processImages(editingElement);
    }
    apply({ isPreviewing, editingElement, params: { mainParam: mode }, loadResult }) {
        if (mode !== this.dependencies.imageGalleryOption.getMode(editingElement)) {
            this.dependencies.imageGalleryOption.setImages(editingElement, mode, loadResult.images);
            this.dependencies.imageGalleryOption.restoreSelection(
                loadResult.imageToSelect,
                isPreviewing
            );
        }
    }
    isApplied({ editingElement, params: { mainParam: mode } }) {
        return mode === this.dependencies.imageGalleryOption.getMode(editingElement);
    }
}
export class SetImageGalleryColumnsAction extends BuilderAction {
    static id = "setImageGalleryColumns";
    static dependencies = ["imageGalleryOption"];
    load({ editingElement }) {
        return this.dependencies.imageGalleryOption.processImages(editingElement);
    }
    apply({ isPreviewing, editingElement, params: { mainParam: columns }, loadResult }) {
        if (columns !== this.dependencies.imageGalleryOption.getColumns(editingElement)) {
            editingElement.dataset.columns = columns;
            this.dependencies.imageGalleryOption.setImages(
                editingElement,
                this.dependencies.imageGalleryOption.getMode(editingElement),
                loadResult.images
            );
            this.dependencies.imageGalleryOption.restoreSelection(
                loadResult.imageToSelect,
                isPreviewing
            );
        }
    }
    isApplied({ editingElement, params: { mainParam: columns } }) {
        return columns === this.dependencies.imageGalleryOption.getColumns(editingElement);
    }
}

export class IndicatorsStyleClassAction extends ClassAction {
    static id = "indicatorsStyle";
    apply({ editingElement, params: { mainParam: className } }) {
        super.apply(...arguments);
        if (editingElement.matches(".s_image_gallery_indicators_outline")) {
            // Remove the outline helper when the chosen indicator style no
            // longer offers that option.
            if (
                ![
                    "s_image_gallery_indicators_squared",
                    "s_image_gallery_indicators_rounded",
                ].includes(className)
            ) {
                editingElement.classList.remove("s_image_gallery_indicators_outline");
            }
        }
    }
}

registry.category("website-plugins").add(ImageGalleryOptionPlugin.id, ImageGalleryOptionPlugin);
