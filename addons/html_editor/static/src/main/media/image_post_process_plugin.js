import {
    activateCropper,
    getAspectRatio,
    getDataURLBinarySize,
    getImageSizeFromCache,
    isGif,
    isWebGLEnabled,
    loadImage,
    loadImageDataURL,
    loadImageInfo,
} from "@html_editor/utils/image_processing";
import { Plugin } from "../../plugin";
import { getAffineApproximation, getProjective } from "@html_editor/utils/perspective_utils";

export const DEFAULT_IMAGE_QUALITY = "92";

/**
 * @typedef { Object } ImagePostProcessShared
 * @property { ImagePostProcessPlugin['processImage'] } processImage
 * @property { ImagePostProcessPlugin['getProcessedImageSize'] } getProcessedImageSize
 */

/**
 * @typedef {(
 *   (img: HTMLImageElement, newDataset: object) => Promise<{
 *     getHeight: (canvas: HTMLCanvasElement) => number,
 *     perspective: string | null,
 *     newDataset: object,
 *     postProcessCroppedCanvas: (canvas: HTMLCanvasElement) => Promise<HTMLCanvasElement>,
 *     svg: SVGElement,
 *     svgAspectRatio: number,
 *     svgWidth: number,
 *   }>
 * )[]} process_image_warmup_handlers
 * @typedef {(
 *   (
 *     url: string,
 *     newDataset: object,
 *     processContext: { svg: SVGElement, svgAspectRatio: number, svgWidth: number }
 *   ) => Promise<[newUrl: string, handlerDataset: object]>
 * )[]} process_image_post_handlers
 * @typedef {((args: {imageEl: HTMLElement}) => void)[]} on_image_updated_handlers
 */

export class ImagePostProcessPlugin extends Plugin {
    static id = "imagePostProcess";
    static dependencies = ["style"];
    static shared = ["processImage", "getProcessedImageSize"];

    /**
     * Applies data-attributes modifications to an img tag and returns a dataURL
     * containing the result. This function does not modify the original image.
     *
     * @param {HTMLImageElement} img the image to which modifications are applied
     * @param {Object} newDataset an object containing the modifications to apply
     * @param {Function} [onImageInfoLoaded] can be used to fill
     * newDataset after having access to image info, return true to cancel call
     * @returns {{ url: string, newDataset: object }} Object containing the image
     * URL and the updated dataset.
     */
    async _processImage({ img, newDataset = {}, onImageInfoLoaded }) {
        const processContext = {};
        if (!newDataset.originalSrc || !newDataset.mimetypeBeforeConversion) {
            Object.assign(newDataset, await loadImageInfo(img));
        }
        if (onImageInfoLoaded) {
            if (await onImageInfoLoaded(newDataset)) {
                return;
            }
        }
        for (const cb of this.getResource("process_image_warmup_handlers")) {
            const addedContext = await cb(img, newDataset);
            if (addedContext) {
                if (addedContext.newDataset) {
                    Object.assign(newDataset, addedContext.newDataset);
                }
                Object.assign(processContext, addedContext);
            }
        }

        const data = getImageTransformationData({ ...img.dataset, ...newDataset });
        const {
            mimetypeBeforeConversion,
            formatMimetype,
            width,
            height,
            resizeWidth,
            filter,
            glFilter,
            filterOptions,
            aspectRatio,
            quality,
        } = data;

        const { postProcessCroppedCanvas, perspective, getHeight } = processContext;

        // loadImage may have ended up loading a different src (see: LOAD_IMAGE_404)
        const originalImg = await loadImage(data.originalSrc);
        const originalSrc = originalImg.getAttribute("src");

        if (shouldPreventGifTransformation(data)) {
            const [postUrl, postDataset] = await this.postProcessImage(
                await loadImageDataURL(originalSrc),
                newDataset,
                processContext
            );
            return { url: postUrl, newDataset: postDataset };
        }
        // Crop
        const container = document.createElement("div");
        container.appendChild(originalImg);
        const cropper = await activateCropper(originalImg, aspectRatio, data);
        const croppedCanvas = cropper.getCroppedCanvas(width, height);
        cropper.destroy();
        const processedCanvas = (await postProcessCroppedCanvas?.(croppedCanvas)) || croppedCanvas;

        // Width
        const canvas = document.createElement("canvas");
        canvas.width = resizeWidth || processedCanvas.width;
        canvas.height = getHeight
            ? getHeight(canvas)
            : (processedCanvas.height * canvas.width) / processedCanvas.width;
        const ctx = canvas.getContext("2d");
        ctx.imageSmoothingQuality = "high";
        ctx.mozImageSmoothingEnabled = true;
        ctx.webkitImageSmoothingEnabled = true;
        ctx.msImageSmoothingEnabled = true;
        ctx.imageSmoothingEnabled = true;

        // Perspective 3D
        if (perspective) {
            // x, y coordinates of the corners of the image as a percentage
            // (relative to the width or height of the image) needed to apply
            // the 3D effect.
            const points = JSON.parse(perspective);
            const divisions = 10;
            const w = processedCanvas.width,
                h = processedCanvas.height;

            const project = getProjective(w, h, [
                [(canvas.width / 100) * points[0][0], (canvas.height / 100) * points[0][1]], // Top-left [x, y]
                [(canvas.width / 100) * points[1][0], (canvas.height / 100) * points[1][1]], // Top-right [x, y]
                [(canvas.width / 100) * points[2][0], (canvas.height / 100) * points[2][1]], // bottom-right [x, y]
                [(canvas.width / 100) * points[3][0], (canvas.height / 100) * points[3][1]], // bottom-left [x, y]
            ]);

            for (let i = 0; i < divisions; i++) {
                for (let j = 0; j < divisions; j++) {
                    const [dx, dy] = [w / divisions, h / divisions];

                    const upper = {
                        origin: [i * dx, j * dy],
                        sides: [dx, dy],
                        flange: 0.1,
                        overlap: 0,
                    };
                    const lower = {
                        origin: [i * dx + dx, j * dy + dy],
                        sides: [-dx, -dy],
                        flange: 0,
                        overlap: 0.1,
                    };

                    for (const { origin, sides, flange, overlap } of [upper, lower]) {
                        const [[a, c, e], [b, d, f]] = getAffineApproximation(project, [
                            origin,
                            [origin[0] + sides[0], origin[1]],
                            [origin[0], origin[1] + sides[1]],
                        ]);

                        const ox = (i !== divisions ? overlap * sides[0] : 0) + flange * sides[0];
                        const oy = (j !== divisions ? overlap * sides[1] : 0) + flange * sides[1];

                        origin[0] += flange * sides[0];
                        origin[1] += flange * sides[1];

                        sides[0] -= flange * sides[0];
                        sides[1] -= flange * sides[1];

                        ctx.save();
                        ctx.setTransform(a, b, c, d, e, f);

                        ctx.beginPath();
                        ctx.moveTo(origin[0] - ox, origin[1] - oy);
                        ctx.lineTo(origin[0] + sides[0], origin[1] - oy);
                        ctx.lineTo(origin[0] + sides[0], origin[1]);
                        ctx.lineTo(origin[0], origin[1] + sides[1]);
                        ctx.lineTo(origin[0] - ox, origin[1] + sides[1]);
                        ctx.closePath();
                        ctx.clip();
                        ctx.drawImage(processedCanvas, 0, 0);

                        ctx.restore();
                    }
                }
            }
        } else {
            ctx.drawImage(
                processedCanvas,
                0,
                0,
                processedCanvas.width,
                processedCanvas.height,
                0,
                0,
                canvas.width,
                canvas.height
            );
        }

        // GL filter
        const canUseWebGL = glFilter && isWebGLEnabled() && window.WebGLImageFilter;
        if (canUseWebGL) {
            const glf = new window.WebGLImageFilter();
            const cv = document.createElement("canvas");
            cv.width = canvas.width;
            cv.height = canvas.height;
            applyAll = _applyAll.bind(null, canvas);
            glFilters[glFilter](glf, cv, filterOptions);
            const filtered = glf.apply(canvas);
            ctx.drawImage(
                filtered,
                0,
                0,
                filtered.width,
                filtered.height,
                0,
                0,
                canvas.width,
                canvas.height
            );
        }

        // Color filter
        ctx.fillStyle = filter || "#0000";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Quality
        newDataset.mimetype = formatMimetype || mimetypeBeforeConversion;
        const dataURL = canvas.toDataURL(newDataset.mimetype, quality / 100);
        const newSize = getDataURLBinarySize(dataURL);
        const originalSize = getImageSizeFromCache(originalSrc);
        const isChanged =
            !!perspective ||
            !!glFilter ||
            originalImg.width !== canvas.width ||
            originalImg.height !== canvas.height ||
            originalImg.width !== processedCanvas.width ||
            originalImg.height !== processedCanvas.height;

        let url =
            isChanged || originalSize >= newSize ? dataURL : await loadImageDataURL(originalSrc);
        [url, newDataset] = await this.postProcessImage(url, newDataset, processContext);
        return { url, newDataset };
    }
    async processImage(params) {
        const processed = await this._processImage(params);
        if (!processed) {
            return () => {};
        }
        return () => this.updateImageAttributes(params.img, processed.url, processed.newDataset);
    }
    async getProcessedImageSize(img) {
        const processed = await this._processImage({ img });
        return getDataURLBinarySize(processed.url);
    }
    async postProcessImage(url, newDataset, processContext) {
        for (const cb of this.getResource("process_image_post_handlers")) {
            const [newUrl, handlerDataset] = (await cb(url, newDataset, processContext)) || [];
            url = newUrl || url;
            newDataset = handlerDataset || newDataset;
        }
        return [url, newDataset];
    }
    updateImageAttributes(el, url, newDataset) {
        el.classList.add("o_modified_image_to_save");
        if (el.tagName === "IMG") {
            el.setAttribute("src", url);
        } else {
            this.dependencies.style.setBackgroundImageUrl(el, url);
        }
        for (const key in newDataset) {
            const value = newDataset[key];
            if (value) {
                el.dataset[key] = value;
            } else {
                delete el.dataset[key];
            }
        }
        this.dispatchTo("on_image_updated_handlers", { imageEl: el });
    }
}

export function getImageTransformationData(dataset) {
    const data = Object.assign(
        {
            glFilter: "",
            filter: "#0000",
            forceModification: false,
        },
        dataset
    );
    for (const key of ["width", "height", "resizeWidth"]) {
        data[key] = parseFloat(data[key]);
    }
    if (!("quality" in data)) {
        data.quality = DEFAULT_IMAGE_QUALITY;
    }
    // todo: this information could be inferred from x/y/width/height dataset
    // properties.
    data.aspectRatio = data.aspectRatio ? getAspectRatio(data.aspectRatio) : 0;
    return data;
}

function shouldTransformImage(data) {
    return (
        data.perspective ||
        data.glFilter ||
        data.width ||
        data.height ||
        data.resizeWidth ||
        data.aspectRatio
    );
}

export function shouldPreventGifTransformation(data) {
    return isGif(data.mimetypeBeforeConversion) && !shouldTransformImage(data);
}

export const defaultImageFilterOptions = {
    blend: "normal",
    filterColor: "",
    blur: "0",
    desaturateLuminance: "0",
    saturation: "0",
    contrast: "0",
    brightness: "0",
    sepia: "0",
};

// webgl color filters
const _applyAll = (result, filter, filters) => {
    filters.forEach((f) => {
        if (f[0] === "blend") {
            const cv = f[1];
            const ctx = result.getContext("2d");
            ctx.globalCompositeOperation = f[2];
            ctx.globalAlpha = f[3];
            ctx.drawImage(cv, 0, 0);
            ctx.globalCompositeOperation = "source-over";
            ctx.globalAlpha = 1.0;
        } else {
            filter.addFilter(...f);
        }
    });
};
let applyAll;

const glFilters = {
    blur: (filter) => filter.addFilter("blur", 10),

    1977: (filter, cv) => {
        const ctx = cv.getContext("2d");
        ctx.fillStyle = "rgb(243, 106, 188)";
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "screen", 0.3],
            ["brightness", 0.1],
            ["contrast", 0.1],
            ["saturation", 0.3],
        ]);
    },

    aden: (filter, cv) => {
        const ctx = cv.getContext("2d");
        ctx.fillStyle = "rgb(66, 10, 14)";
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "darken", 0.2],
            ["brightness", 0.2],
            ["contrast", -0.1],
            ["saturation", -0.15],
            ["hue", 20],
        ]);
    },

    brannan: (filter, cv) => {
        const ctx = cv.getContext("2d");
        ctx.fillStyle = "rgb(161, 44, 191)";
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "lighten", 0.31],
            ["sepia", 0.5],
            ["contrast", 0.4],
        ]);
    },

    earlybird: (filter, cv) => {
        const ctx = cv.getContext("2d");
        const gradient = ctx.createRadialGradient(
            cv.width / 2,
            cv.height / 2,
            0,
            cv.width / 2,
            cv.height / 2,
            Math.hypot(cv.width, cv.height) / 2
        );
        gradient.addColorStop(0.2, "#D0BA8E");
        gradient.addColorStop(1, "#1D0210");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "overlay", 0.2],
            ["sepia", 0.2],
            ["contrast", -0.1],
        ]);
    },

    inkwell: (filter, cv) => {
        applyAll(filter, [
            ["sepia", 0.3],
            ["brightness", 0.1],
            ["contrast", -0.1],
            ["desaturateLuminance"],
        ]);
    },

    // Needs hue blending mode for perfect reproduction. Close enough?
    maven: (filter, cv) => {
        applyAll(filter, [
            ["sepia", 0.25],
            ["brightness", -0.05],
            ["contrast", -0.05],
            ["saturation", 0.5],
        ]);
    },

    toaster: (filter, cv) => {
        const ctx = cv.getContext("2d");
        const gradient = ctx.createRadialGradient(
            cv.width / 2,
            cv.height / 2,
            0,
            cv.width / 2,
            cv.height / 2,
            Math.hypot(cv.width, cv.height) / 2
        );
        gradient.addColorStop(0, "#0F4E80");
        gradient.addColorStop(1, "#3B003B");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "screen", 0.5],
            ["brightness", -0.1],
            ["contrast", 0.5],
        ]);
    },

    walden: (filter, cv) => {
        const ctx = cv.getContext("2d");
        ctx.fillStyle = "#CC4400";
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "screen", 0.3],
            ["sepia", 0.3],
            ["brightness", 0.1],
            ["saturation", 0.6],
            ["hue", 350],
        ]);
    },

    valencia: (filter, cv) => {
        const ctx = cv.getContext("2d");
        ctx.fillStyle = "#3A0339";
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "exclusion", 0.5],
            ["sepia", 0.08],
            ["brightness", 0.08],
            ["contrast", 0.08],
        ]);
    },

    xpro: (filter, cv) => {
        const ctx = cv.getContext("2d");
        const gradient = ctx.createRadialGradient(
            cv.width / 2,
            cv.height / 2,
            0,
            cv.width / 2,
            cv.height / 2,
            Math.hypot(cv.width, cv.height) / 2
        );
        gradient.addColorStop(0.4, "#E0E7E6");
        gradient.addColorStop(1, "#2B2AA1");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "color-burn", 0.7],
            ["sepia", 0.3],
        ]);
    },

    custom: (filter, cv, filterOptions) => {
        const options = Object.assign(defaultImageFilterOptions, JSON.parse(filterOptions || "{}"));
        const filters = [];
        if (options.filterColor) {
            const ctx = cv.getContext("2d");
            ctx.fillStyle = options.filterColor;
            ctx.fillRect(0, 0, cv.width, cv.height);
            filters.push(["blend", cv, options.blend, 1]);
        }
        delete options.blend;
        delete options.filterColor;
        filters.push(
            ...Object.entries(options).map(([filter, amount]) => [filter, parseInt(amount) / 100])
        );
        applyAll(filter, filters);
    },
};
