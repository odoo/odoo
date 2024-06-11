/** @odoo-module **/

import { registry } from "@web/core/registry";
import { canExportCanvasAsWebp, convertCanvasToDataURL } from "@web/core/utils/image_processing";

export const IMAGE_TYPE = {
    WEBP: {
        mimetype: "image/webp",
        extension: "webp",
    },
    JPEG: {
        mimetype: "image/jpeg",
        extension: "jpeg",
    },
    PNG: {
        mimetype: "image/png",
        extension: "png",
    },
};

export const STANDARD_ALTERNATIVE_TYPES = [IMAGE_TYPE.WEBP, IMAGE_TYPE.JPEG];
export const STANDARD_ALTERNATIVE_SIZES = [1024, 512, 256, 128];

/**
 * Looks up the extension for the given mimetype from {@link IMAGE_TYPE}
 *
 * @returns {string}
 */
export function getImageExtensionForMimetype(mimetype) {
    return Object.values(IMAGE_TYPE).find((type) => type.mimetype === mimetype).extension;
}

export class ImageProcessingService {
    static dependencies = ["orm"];

    constructor() {
        this.setup(...arguments);
    }

    setup(env, { orm }) {
        this.orm = orm;
    }

    /**
     * Generate alternative sizes for a given image, image sizes and types {@link IMAGE_TYPE}.
     * Only available types are generated.
     * Optionally save the generated images as an attachment tree (Original image > First image of size > Other types)
     *
     * @param {string} src
     * @param {number} quality See {@link HTMLCanvasElement.toDataURL}
     * @param {boolean} [doSave] Whether to save
     * @param {string} [fileBasename] File basename for saved attachments
     * @param {number[]} [requestedSizes] {@link IMAGE_TYPE}
     * @param {{ mimetype: string, extension: string }[]} [imageTypes] {@link IMAGE_TYPE}
     * @return {Promise<{
     *  originalImage: {} | undefined,
     *  alternativeImagesBySize: Record<number, { dataURL: string, mimetype: string }>
     * }>} originalImage is only provided when `doSave === true`.
     */
    async generateImageAlternatives(
        src,
        quality,
        doSave = false,
        fileBasename = undefined,
        requestedSizes = STANDARD_ALTERNATIVE_SIZES,
        imageTypes = STANDARD_ALTERNATIVE_TYPES
    ) {
        const imageElement = await this._makeImageElementForProcessing(src);
        const { originalSize, alternativeSizes } = this._getImageElementAlternativeSizes(
            imageElement,
            requestedSizes
        );

        const alternativeImagesBySize = {};
        for (const size of [originalSize, ...alternativeSizes]) {
            const availableImageTypes = imageTypes.filter(
                (imageType) => imageType.mimetype !== "image/webp" || canExportCanvasAsWebp()
            );
            const canvas = this._makeCanvasForImage(imageElement, size, originalSize);
            alternativeImagesBySize[size] = this._getAlternativeImagesFromCanvas(
                canvas,
                quality,
                availableImageTypes
            );
        }

        let originalImage = undefined;

        if (doSave) {
            originalImage = await this._saveAlternativeImageSizesAttachments(
                alternativeImagesBySize,
                originalSize,
                fileBasename
            );
        }

        return {
            originalImage: originalImage,
            alternativeImagesBySize: alternativeImagesBySize,
        };
    }

    /**
     * Saves images as attachment tree.
     *
     * @param alternativeImagesBySize {Record<number, { dataURL: string, mimetype: string }>} Lists of images by size
     * @param originalSize {number}
     * @param fileBasename {string}
     * @returns {Promise<{ id: number, dataURL: string, mimetype: string }>} The original image's data
     */
    async _saveAlternativeImageSizesAttachments(
        alternativeImagesBySize,
        originalSize,
        fileBasename
    ) {
        let originalId = undefined;
        let originalImage = undefined;
        for (const size in alternativeImagesBySize) {
            const images = alternativeImagesBySize[size];
            const isOriginalSize = size === originalSize.toString();

            let sizeRootId = undefined;

            for (const image of images) {
                const extension = getImageExtensionForMimetype(image.mimetype);

                let description;
                if (sizeRootId === undefined) {
                    description = isOriginalSize ? "" : `resize: ${size}`;
                } else {
                    description = `format: ${extension}`;
                }

                const attachmentData = {
                    res_model: "ir.attachment",
                    name: `${fileBasename}.${extension}`,
                    description: description,
                    datas: image.dataURL.split(",")[1],
                    res_id: sizeRootId || originalId,
                    mimetype: image.mimetype,
                };
                const [attachmentId] = await this.orm.call("ir.attachment", "create_unique", [
                    [attachmentData],
                ]);

                sizeRootId = sizeRootId || attachmentId;
                originalId = originalId || attachmentId;
                originalImage = originalImage || image;
            }
        }

        return {
            id: originalId,
            ...originalImage,
        };
    }

    async _makeImageElementForProcessing(src) {
        const imageElement = document.createElement("img");
        imageElement.src = src;
        await new Promise((resolve) => imageElement.addEventListener("load", resolve));
        return imageElement;
    }

    _getImageElementAlternativeSizes(imageElement, requestedSizes) {
        const originalSize = Math.max(imageElement.width, imageElement.height);
        const smallerSizes = requestedSizes.filter((size) => size < originalSize);
        return {
            originalSize: originalSize,
            alternativeSizes: smallerSizes,
        };
    }

    _makeCanvasForImage(imageElement, size, originalSize) {
        const ratio = size / originalSize;
        const canvas = document.createElement("canvas");
        canvas.width = imageElement.width * ratio;
        canvas.height = imageElement.height * ratio;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "rgb(255, 255, 255)";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(
            imageElement,
            0,
            0,
            imageElement.width,
            imageElement.height,
            0,
            0,
            canvas.width,
            canvas.height
        );
        return canvas;
    }

    _getAlternativeImagesFromCanvas(canvas, quality, imageTypes) {
        const imageDatas = [];
        for (const imageType of imageTypes) {
            const { dataURL, mimetype } = convertCanvasToDataURL(
                canvas,
                imageType.mimetype,
                quality
            );
            imageDatas.push({
                dataURL: dataURL,
                mimetype: mimetype,
            });
        }
        return imageDatas;
    }
}

export const imageProcessingService = {
    dependencies: ImageProcessingService.dependencies,
    start() {
        return new ImageProcessingService(...arguments);
    },
};

registry.category("services").add("image_processing", imageProcessingService);
