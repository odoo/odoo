import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { applyModifications, loadImageInfo } from "@html_editor/utils/image_processing";

class ImageGalleryOption extends Plugin {
    static id = "ImageGalleryOption";
    static dependencies = ["media", "dom", "history"];
    resources = {
        builder_options: [
            {
                template: "html_builder.ImageGalleryOption",
                selector: ".s_image_gallery",
            },
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            addImage: {
                load: async ({ editingElement }) => {
                    let selectedImages;
                    await new Promise((resolve) => {
                        this.dependencies.media.openMediaDialog({
                            onlyImages: true,
                            multiImages: true,
                            save: (images) => {
                                selectedImages = images;
                                resolve();
                            },
                        });
                    });
                    await transformImagesToWebp(selectedImages);
                    setImageProperties(editingElement, selectedImages);
                    const clonedContainerImg = await cloneContainerImages(editingElement);
                    return [...clonedContainerImg, ...selectedImages];
                },
                apply: ({ editingElement, loadResult: images }) => {
                    setImages(editingElement, images);
                },
            },
            removeAllImages: {
                // TODO: implement the remove images
                apply: () => console.log("Remove all"),
            },
        };
    }
}

/**
 * Add the images selected in the media dialog in the gallery
 */
async function setImages(imageGalleryElement, images) {
    if (getMode(imageGalleryElement) === "masonry") {
        masonry(imageGalleryElement, images);
    }
}

function setImageProperties(imageGalleryElement, images) {
    const lastImage = getImages(imageGalleryElement).at(-1);
    let lastIndex = lastImage ? getIndex(lastImage) : -1;
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

async function transformImagesToWebp(images) {
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

function masonry(imageGalleryElement, images) {
    const columnsNumber = getColumns(imageGalleryElement);
    const colClass = "col-lg-" + 12 / columnsNumber;
    const columns = [];

    const row = document.createElement("div");
    row.classList.add("row", "s_nb_column_fixed");
    getContainer(imageGalleryElement).replaceChildren(row);

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
                imagesInCol.length && imagesInCol[imagesInCol.length - 1].getBoundingClientRect();
            const height = lastImageRect ? Math.round(lastImageRect.top + lastImageRect.height) : 0;
            if (height < min) {
                min = height;
                smallestColEl = colEl;
            }
        }
        smallestColEl.append(imageEl);
    }
}

/**
 * Get the image target's layout mode (slideshow, masonry, grid or nomode).
 *
 * @returns {String('slideshow'|'masonry'|'grid'|'nomode')}
 */
function getMode(imageGalleryElement) {
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

function getImages(currentContainer) {
    const imgs = currentContainer.querySelectorAll("img");
    return [...imgs].sort((imgA, imgB) => getIndex(imgA) - getIndex(imgB));
}

function getIndex(img) {
    return parseInt(img.dataset.index) || 0;
}

function getImageHolder(currentContainer) {
    const images = getImages(currentContainer);
    return [...images].map((image) => image.closest("a") || image);
}

async function cloneContainerImages(imageGalleryElement) {
    const imagesHolder = getImageHolder(imageGalleryElement);
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
 * Relayout the imageGalleryElement with the "masonry" layout.
 * @param {Element} imageGalleryElement
 */

function getColumns(imageGalleryElement) {
    return parseInt(imageGalleryElement.dataset.columns) || 3;
}

function getContainer(imageGalleryElement) {
    return imageGalleryElement.querySelector(".container, .container-fluid, .o_container_small");
}

registry.category("website-plugins").add(ImageGalleryOption.id, ImageGalleryOption);
