import { Plugin } from "@html_editor/plugin";
import {
    backgroundImageCssToParts,
    backgroundImagePartsToCss,
    getImageSrc,
} from "@html_editor/utils/image";
import { loadImage } from "@html_editor/utils/image_processing";
import { rpc } from "@web/core/network/rpc";

/**
 * @typedef { Object } ImageSaveShared
 * @property { ImageSavePlugin['savePendingImages'] } savePendingImages
 */

/**
 * @typedef {((el: HTMLElement) => HTMLElement)[]} closest_savable_providers
 *
 * @typedef {((args: {imageEl: HTMLElement}) => void)[]} on_image_saved_handlers
 */

export class ImageSavePlugin extends Plugin {
    static id = "imageSave";
    static shared = ["savePendingImages"];
    static dependencies = ["imagePostProcess"];

    /** @type {import("plugins").EditorResources} */
    resources = {
        before_save_handlers: this.savePendingImages.bind(this),

        ...(this.config.dropImageAsAttachment && {
            added_image_handlers: (img) => img.classList.add("o_b64_image_to_save"),
        }),
    };

    async savePendingImages(editableEl = this.editable) {
        // When saving a webp, o_b64_image_to_save is turned into
        // o_modified_image_to_save by saveB64Image to request the saving
        // of the pre-converted webp resizes and all the equivalent jpgs.
        const getClosestSavable = (el) => {
            for (const provider of this.getResource("closest_savable_providers")) {
                const value = provider(el);
                if (value) {
                    return value;
                }
            }
        };
        const oldSrcToNewSrcMap = new Map();
        const b64Proms = [...editableEl.querySelectorAll(".o_b64_image_to_save")].map(
            async (el) => {
                const { resModel, resId } = this.getRecordInfo(getClosestSavable(el));
                const oldSrc = el.getAttribute("src");
                await this.saveB64Image(el, resModel, resId);
                oldSrcToNewSrcMap.set(oldSrc, el.getAttribute("src"));
            }
        );
        const modifiedProms = [...editableEl.querySelectorAll(".o_modified_image_to_save")].map(
            async (el) => {
                const { resModel, resId } = this.getRecordInfo(getClosestSavable(el));
                const oldSrc = el.getAttribute("src");
                await this.saveModifiedImage(el, resModel, resId);
                oldSrcToNewSrcMap.set(oldSrc, el.getAttribute("src"));
            }
        );
        const proms = [...b64Proms, ...modifiedProms];
        const hasChange = !!proms.length;
        if (hasChange) {
            await Promise.all(proms);
        }
        return hasChange ? oldSrcToNewSrcMap : undefined;
    }

    createAttachment({ el, imageData, resModel, resId }) {
        return rpc("/html_editor/attachment/add_data", {
            name: el.dataset.fileName || "",
            data: imageData,
            is_image: true,
            res_model: resModel,
            res_id: resId,
        });
    }

    /**
     * Saves a base64 encoded image as an attachment.
     * Relies on saveModifiedImage being called after it for webp.
     *
     * @private
     * @param {Element} el
     * @param {string} resModel
     * @param {number} resId
     */
    async saveB64Image(el, resModel, resId) {
        const imageData = el.getAttribute("src").split("base64,")[1];
        if (!imageData) {
            // Checks if the image is in base64 format for RPC call. Relying
            // only on the presence of the class "o_b64_image_to_save" is not
            // robust enough.
            el.classList.remove("o_b64_image_to_save");
            return;
        }
        const attachment = await this.createAttachment({
            el,
            imageData,
            resId,
            resModel,
        });
        if (!attachment) {
            return;
        }
        if (attachment.mimetype === "image/webp") {
            el.classList.add("o_modified_image_to_save");
            el.dataset.originalId = attachment.id;
            el.dataset.mimetype = attachment.mimetype;
            el.dataset.fileName = attachment.name;
            return this.saveModifiedImage(el, resModel, resId);
        } else {
            let src = attachment.image_src;
            if (!attachment.public) {
                let accessToken = attachment.access_token;
                if (!accessToken) {
                    [accessToken] = await this.services.orm.call(
                        "ir.attachment",
                        "generate_access_token",
                        [attachment.id]
                    );
                }
                src += `?access_token=${encodeURIComponent(accessToken)}`;
            }
            el.setAttribute("src", src);
        }
        el.classList.remove("o_b64_image_to_save");
    }
    imageIsGif(el) {
        if (el.dataset.mimetype === "image/svg+xml") {
            const rawData = getImageSrc(el).split(",")[1];
            const svgData = atob(rawData);
            return svgData.includes("data:image/gif");
        }
        return el.dataset.mimetype === "image/gif";
    }
    /**
     * Saves a modified image as an attachment.
     *
     * @private
     * @param {Element} el
     * @param {string} resModel
     * @param {number} resId
     */
    async saveModifiedImage(el, resModel, resId) {
        const isBackground = !el.matches("img");
        // Modifying an image always creates a copy of the original, even if
        // it was modified previously, as the other modified image may be used
        // elsewhere if the snippet was duplicated or was saved as a custom one.
        let altData = undefined;
        const altImages = {};
        const isImageField = !!el.closest("[data-oe-type=image]");

        const loadedImgEl = await loadImage(getImageSrc(el));
        const maxSize = loadedImgEl.width;
        if (el.dataset.mimetype === "image/webp" && isImageField) {
            // Generate alternate sizes and format for reports.
            altData = {};
            const originalSize = Math.max(loadedImgEl.width, loadedImgEl.height);
            const smallerSizes = [1024, 512, 256, 128].filter((size) => size < originalSize);
            for (const size of [originalSize, ...smallerSizes]) {
                const ratio = size / originalSize;
                const canvas = document.createElement("canvas");
                canvas.width = loadedImgEl.width * ratio;
                canvas.height = loadedImgEl.height * ratio;
                const ctx = canvas.getContext("2d");
                ctx.fillStyle = "rgb(255, 255, 255)";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(
                    loadedImgEl,
                    0,
                    0,
                    loadedImgEl.width,
                    loadedImgEl.height,
                    0,
                    0,
                    canvas.width,
                    canvas.height
                );
                altData[size] = {
                    "image/jpeg": canvas.toDataURL("image/jpeg").split(",")[1],
                };
                if (size !== originalSize) {
                    altData[size]["image/webp"] = canvas.toDataURL("image/webp").split(",")[1];
                }
            }
        }
        if (!isImageField && !isBackground && !this.imageIsGif(el) && !el.dataset.hoverEffect) {
            // We are using these sizes instead of the normally used 128, 256, ...
            // because we want to optimize smartphone data usage and loading time.
            // Each sizes in smallerSizes fits a certain category of smartphone,
            // while still limiting the number of image generated.
            const smallerSizes = [750, 900, 1080, 1280].filter(
                // We only generate sizes smaller than 85% of the original size
                (size) => size < Math.floor(maxSize * 0.85)
            );
            if (smallerSizes.length) {
                const imgCloneEl = el.cloneNode(true);
                for (const size of smallerSizes) {
                    const updateImageSize = await this.dependencies.imagePostProcess.processImage({
                        img: imgCloneEl,
                        newDataset: { resizeWidth: size },
                    });
                    updateImageSize();
                    if (getImageSrc(imgCloneEl)) {
                        altImages[size] = this.getImageBase64Payload(imgCloneEl);
                    }
                }
            }
        }
        const newAttachmentUrls = await rpc(
            `/html_editor/modify_image/${encodeURIComponent(el.dataset.originalId)}`,
            {
                res_model: resModel,
                res_id: parseInt(resId),
                data: this.getImageBase64Payload(el),
                alt_data: altData,
                alt_images: Object.keys(altImages).length ? altImages : null,
                mimetype: isBackground
                    ? el.dataset.mimetype
                    : el.getAttribute("src").split(":")[1].split(";")[0],
                name: el.dataset.fileName ? el.dataset.fileName : null,
            }
        );

        const srcset = [];
        if (Object.keys(altImages).length) {
            for (const size in altImages) {
                if (newAttachmentUrls[size]) {
                    srcset.push(`${newAttachmentUrls[size]} ${size}w`);
                }
            }
            srcset.push(`${newAttachmentUrls["original"]} ${maxSize}w`);
        }

        el.classList.remove("o_modified_image_to_save");
        if (isBackground) {
            const parts = backgroundImageCssToParts(el.style["background-image"]);
            parts.url = `url('${newAttachmentUrls["original"]}')`;
            const combined = backgroundImagePartsToCss(parts);
            el.style["background-image"] = combined;
        } else {
            el.setAttribute("src", newAttachmentUrls["original"]);
            if (srcset.length) {
                el.setAttribute("srcset", srcset.join(", "));
            }
        }
        this.dispatchTo("on_image_saved_handlers", { imageEl: el });
    }

    getImageBase64Payload(el) {
        return getImageSrc(el).split(",")[1];
    }

    getRecordInfo(editableEl = null) {
        return this.config.getRecordInfo ? this.config.getRecordInfo(editableEl) : {};
    }
}
