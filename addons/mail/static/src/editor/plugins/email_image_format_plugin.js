import { Plugin } from "@html_editor/plugin";
import { hasTextColorClass } from "@html_editor/utils/color";
import { childNodes, selectElements } from "@html_editor/utils/dom_traversal";
import {
    backgroundImageCssToParts,
    backgroundImagePartsToCss,
    getImageSrc,
} from "@html_editor/utils/image";
import { loadImage, loadImageInfo } from "@html_editor/utils/image_processing";
import { parseCssValue } from "@mail/convert_inline/css_parsers";
import { registry } from "@web/core/registry";
import { extractGradientData } from "@web/core/utils/colors";
import { generateHTMLId } from "@web/core/utils/strings";
import {
    computeEmailImageChecksum,
    normalizeDimensions,
    normalizePosition,
} from "./email_image_checksum_generator";
import { rpc } from "@web/core/network/rpc";

const SVG_MIMETYPE = "image/svg+xml";
const WEBP_MIMETYPE = "image/webp";
const FORBIDDEN_EMAIL_MIMETYPE = new Set([SVG_MIMETYPE, WEBP_MIMETYPE]);
const SVG_EXCLUSIVE_ATTRIBUTES = new Set(["viewBox", "preserveAspectRatio", "x", "y"]);
const PLACEHOLDER_IMAGE = "/html_editor/static/src/img/placeholder_thumbnail.png";
const EMAIL_IMAGE_RESOLUTION_SCALING = { min: 0.5, max: 2 };

export class AggregateEmailImageError extends AggregateError {
    name = this.constructor.name;
}
export class EmailImageError extends Error {
    name = this.constructor.name;
}
class InvalidEmailImageSourceError extends EmailImageError {}
class EmailImageAttachmentCreationError extends EmailImageError {}

function getDisplayUrl(url) {
    if (!url) {
        url = "";
    }
    url = typeof url === "string" ? url : url.toString();
    return `${url.substring(0, 50)}${url.length > 50 ? "..." : ""}`;
}

export class EmailImageFormatPlugin extends Plugin {
    static id = "emailImageFormat";
    static dependencies = ["imagePostProcess", "imageSave"];
    static shared = ["sanitizeImages"];
    static defaultConfig = {
        // TODO EGGMAIL: if transparency usage can be detected, prefer JPEG over PNG
        // currently there is no transparency detection logic, so PNG is used by default.
        // PNG is the default image format to preserve transparency.
        defaultImageMimetype: "image/png",
    };
    resources = {
        before_clean_for_save_with_pending_images_handlers: this.setImageIdentity.bind(this),
        system_attributes: ["data-oe-nodeid"],
    };

    setup() {
        this.elToNodeid = new WeakMap();
        this.initializeChecksumCache();
    }

    /**
     * TODO EGGMAIL: there seems to be an usage inconsistency between
     * data-original-id and data-attachment-id in html_editor code.
     * data-attachment-id seems to be the newer one, but some code is still
     * using data-original-id.
     */
    getMainAttachmentId(info) {
        return info.originalId === undefined ? info.attachmentId : info.originalId;
    }

    initializeChecksumCache() {
        this.checksumCache = new Map();
        for (const el of selectElements(
            this.editable,
            "[data-email-image-src][data-email-image-checksum]"
        )) {
            const src = el.dataset.emailImageSrc;
            const checksum = el.dataset.emailImageChecksum;
            if (!this.checksumCache.has(checksum)) {
                this.checksumCache.set(checksum, src);
            }
        }
    }

    setImageIdentity() {
        this.nodeidMap = new Map();
        const generateNodeId = (el) => {
            const nodeid = generateHTMLId();
            el.dataset.oeNodeid = nodeid;
            this.nodeidMap.set(nodeid, {
                sourceEl: el,
                measureEl: undefined,
            });
        };
        const ensureBase64Handling = (el) => {
            const src = getImageSrc(el)?.trimStart();
            if (
                src &&
                src.split("base64,")[1] &&
                !el.matches(".o_b64_image_to_save,.o_modified_image_to_save")
            ) {
                if (this.getMainAttachmentId(el.dataset)) {
                    el.classList.add("o_modified_image_to_save");
                } else {
                    el.classList.add("o_b64_image_to_save");
                }
            }
        };
        this.forEachSvg(generateNodeId, this.editable);
        this.forEachImg((img) => {
            generateNodeId(img);
            ensureBase64Handling(img);
        }, this.editable);
        this.forEachBackgroundImg((el) => {
            generateNodeId(el);
            ensureBase64Handling(el);
        }, this.editable);
    }

    cleanupImageIdentity(editable) {
        for (const el of selectElements(editable, "[data-oe-nodeid]")) {
            delete el.dataset.oeNodeid;
        }
    }

    setupReferenceClone(editable) {
        const clone = editable.cloneNode(true);
        const setMeasureEl = (el) => (this.nodeidMap.get(el.dataset.oeNodeid).measureEl = el);
        this.forEachImg(setMeasureEl, clone);
        this.forEachBackgroundImg(setMeasureEl, clone);
        const cloneFragment = this.document.createDocumentFragment();
        cloneFragment.replaceChildren(...childNodes(clone));
        this.measureUtilsPromise = this.config.measureReference(cloneFragment);
        this.measureUtils = undefined;
    }

    /**
     * Ensure that every restricted image/background-image format (SVG/WEBP) is
     * converted to a mail-supported equivalent (PNG).
     */
    async sanitizeImages(editable) {
        this.forEachSvg((svg) => this.sanitizeSvg(svg), editable);
        this.setupReferenceClone(editable);

        const promises = [];
        const sanitizeImage = (el) => {
            const noideidData = this.nodeidMap.get(el.dataset.oeNodeid);
            const { sourceEl, measureEl } = noideidData;
            return this.sanitizeImage(el, sourceEl, measureEl).catch((reason) => {
                this.setEmailImage(PLACEHOLDER_IMAGE, undefined, el, sourceEl);
                throw reason;
            });
        };
        promises.push(...this.forEachImg(sanitizeImage, editable));
        promises.push(...this.forEachBackgroundImg(sanitizeImage, editable));

        // Cleanup data-oe-nodeid from the editable and the clone to save
        this.cleanupImageIdentity(editable);
        this.cleanupImageIdentity(this.editable);

        const results = await Promise.allSettled(promises);
        const errors = [];
        let containsMiscErrors = false;
        for (const result of results) {
            if (result.status !== "rejected") {
                continue;
            }
            errors.push(result.reason);
            if (!(result.reason instanceof EmailImageError)) {
                containsMiscErrors = true;
            }
        }
        if (errors.length === 0) {
            return;
        }
        if (errors.length === 1) {
            throw errors[0];
        }
        if (!containsMiscErrors) {
            throw new AggregateEmailImageError(
                errors,
                "Image conversion to a valid email format failed."
            );
        }
        throw new AggregateError(errors, "Some images could not be processed.");
    }

    async prepare2DCanvasForImg(img, width, height) {
        if (!img.complete) {
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
            });
        }
        await img.decode();

        const canvas = this.document.createElement("canvas");
        canvas.height = height;
        canvas.width = width;
        const ctx = canvas.getContext("2d");
        return { canvas, ctx };
    }

    async convertImgToImageData(img, width, height) {
        const { canvas, ctx } = await this.prepare2DCanvasForImg(img, width, height);
        ctx.drawImage(img, 0, 0, width, height);
        return canvas.toDataURL(this.config.defaultImageMimetype);
    }

    async convertBackgroundToImageData(
        src,
        renderedDimensions,
        targetDimensions,
        targetPosition,
        filterData
    ) {
        const img = new Image();
        img.src = src;
        const { canvas, ctx } = await this.prepare2DCanvasForImg(
            img,
            renderedDimensions.width,
            renderedDimensions.height
        );
        ctx.drawImage(img, 0, 0, renderedDimensions.width, renderedDimensions.height);
        if (filterData) {
            ctx.save();
            if (filterData.color) {
                this.drawColor(ctx, renderedDimensions, filterData.color);
            } else if (filterData.gradient) {
                this.drawGradient(
                    ctx,
                    targetPosition,
                    targetDimensions,
                    renderedDimensions,
                    filterData.gradient
                );
            }
            ctx.restore();
        }
        return canvas.toDataURL(this.config.defaultImageMimetype);
    }

    drawColor(ctx, renderedDimensions, color) {
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, renderedDimensions.width, renderedDimensions.height);
    }

    /**
     * @param {number} angle (radians)
     */
    getLinearGradientEndpoints({ width, height }, angle) {
        const dx = Math.cos(angle);
        const dy = Math.sin(angle);

        const centerX = width / 2;
        const centerY = height / 2;

        const halfLength = Math.abs(width * dx) / 2 + Math.abs(height * dy) / 2;

        return {
            x0: centerX - dx * halfLength,
            y0: centerY - dy * halfLength,
            x1: centerX + dx * halfLength,
            y1: centerY + dy * halfLength,
        };
    }

    resolveCircleRadius(size, centerX, centerY, { width, height }) {
        const left = centerX;
        const right = width - centerX;
        const top = centerY;
        const bottom = height - centerY;

        switch (size) {
            case "closest-side":
                return Math.min(left, right, top, bottom);
            case "farthest-side":
                return Math.max(left, right, top, bottom);
            case "closest-corner":
                return Math.min(
                    Math.hypot(left, top),
                    Math.hypot(right, top),
                    Math.hypot(left, bottom),
                    Math.hypot(right, bottom)
                );
            default: // farthest-corner
                return Math.max(
                    Math.hypot(left, top),
                    Math.hypot(right, top),
                    Math.hypot(left, bottom),
                    Math.hypot(right, bottom)
                );
        }
    }

    drawGradient(ctx, targetPosition, targetDimensions, renderedDimensions, gradientData) {
        let angle, centerX, centerY;
        if (gradientData.angle !== undefined) {
            angle = (gradientData.angle * Math.PI) / 180 - Math.PI / 2;
        }
        if (gradientData.position) {
            centerX = targetPosition.x + (targetDimensions.width * gradientData.position.x) / 100;
            centerY = targetPosition.y + (targetDimensions.height * gradientData.position.y) / 100;
        }
        let gradient;
        if (gradientData.type === "linear") {
            const { x0, y0, x1, y1 } = this.getLinearGradientEndpoints(targetDimensions, angle);
            gradient = ctx.createLinearGradient(
                targetPosition.x + x0,
                targetPosition.y + y0,
                targetPosition.x + x1,
                targetPosition.y + y1
            );
        } else if (gradientData.type === "radial") {
            const radius = this.resolveCircleRadius(
                gradientData.size,
                centerX,
                centerY,
                targetDimensions
            );
            gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
        } else if (gradientData.type === "conic") {
            gradient = ctx.createConicGradient(angle, centerX, centerY);
        }
        if (gradient) {
            for (const colorData of gradientData.colors) {
                gradient.addColorStop(
                    Math.min(1, Math.max(0, colorData.percentage / 100)),
                    colorData.hex
                );
            }
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, renderedDimensions.width, renderedDimensions.height);
        }
    }

    async convertImageDataToEmailAttachmentSrc(imageData, imageInfo) {
        const attachmentId = this.getMainAttachmentId(imageInfo);
        const { resModel, resId } = this.getRecordInfo(this.editable);
        imageData = imageData.substring(imageData.indexOf(",") + 1);
        const newAttachmentUrls = await rpc(
            `/html_editor/modify_image/${encodeURIComponent(attachmentId)}`,
            {
                res_model: resModel,
                res_id: parseInt(resId),
                data: imageData,
                mimetype: this.config.defaultImageMimetype,
                name: `email_${attachmentId}.png`,
            }
        );
        return newAttachmentUrls.original;
    }

    getRecordInfo(img) {
        const getClosestSavable = (el) => {
            for (const provider of this.getResource("closest_savable_providers")) {
                const value = provider(el);
                if (value) {
                    return value;
                }
            }
        };
        const editableEl = getClosestSavable(img);
        return this.config.getRecordInfo ? this.config.getRecordInfo(editableEl) : {};
    }

    throwFetchError(url) {
        throw new InvalidEmailImageSourceError(
            `The image could not be fetched. ${getDisplayUrl(url)}`
        );
    }

    async fetchImageUrl(url) {
        const response = await fetch(url);
        if (!response.ok) {
            this.throwFetchError(url);
        }
        return response;
    }

    async getSvgAspectRatio(svgUrl) {
        const response = await this.fetchImageUrl(svgUrl);
        const text = await response.text();
        const doc = new DOMParser().parseFromString(text, "image/svg+xml");
        const svg = doc.documentElement;
        const viewBox = svg.getAttribute("viewBox");
        if (viewBox) {
            const [, , width, height] = viewBox
                .trim()
                .split(/[\s,]+/)
                .map(Number);

            if (width > 0 && height > 0) {
                return width / height;
            }
        }
        const width = parseFloat(svg.getAttribute("width"));
        const height = parseFloat(svg.getAttribute("height"));
        if (width > 0 && height > 0) {
            return width / height;
        }
        return null;
    }

    async computeSvgNaturalDimensions(src, measuredDimensions) {
        const dimensions = {};
        const aspectRatio = await this.getSvgAspectRatio(src);
        const { width, height } = measuredDimensions;
        // For SVG images, render at measured dimensions since their
        // resolution is dynamic, and they don't necessarily have
        // natural dimensions nor are they relevant.
        dimensions.width = width;
        dimensions.height = height;
        if (aspectRatio !== null) {
            const heightFromWidth = width / aspectRatio;
            const widthFromHeight = height * aspectRatio;
            if (heightFromWidth <= height) {
                dimensions.height = heightFromWidth;
            } else {
                dimensions.width = widthFromHeight;
            }
        }
        return dimensions;
    }

    async urlToDataUrl(url) {
        const response = await this.fetchImageUrl(url);
        const blob = await response.blob();
        if (!blob.type.startsWith("image/")) {
            this.throwFetchError(url);
        }
        return await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    async convertImageDataToEditorAttachment(imageData) {
        imageData = imageData.split("base64,")[1];
        const { resModel, resId } = this.getRecordInfo(this.editable);
        const attachment = await this.dependencies.imageSave.createAttachment({
            imageData,
            resModel,
            resId,
        });
        if (!attachment) {
            return;
        }
        if (!attachment.public) {
            let accessToken = attachment.access_token;
            if (!accessToken) {
                [accessToken] = await this.services.orm.call(
                    "ir.attachment",
                    "generate_access_token",
                    [attachment.id]
                );
            }
            attachment.access_token = accessToken;
        }
        return attachment;
    }

    updateImageData(el, attachment) {
        const src = `${attachment.image_src}${
            attachment.access_token
                ? `?access_token=${encodeURIComponent(attachment.access_token)}`
                : ""
        }`;
        Object.assign(el.dataset, {
            attachmentId: attachment.id,
            mimetype: attachment.mimetype,
            mimetypeBeforeConversion: attachment.mimetype,
            originalId: attachment.id,
            originalSrc: src,
        });
        this.updateImageSource(el, src);
    }

    updateImageSource(el, src) {
        if (el.nodeName === "IMG") {
            el.src = src;
        } else {
            const parts = backgroundImageCssToParts(el.style["background-image"]);
            parts.url = `url('${src}')`;
            const combined = backgroundImagePartsToCss(parts);
            el.style["background-image"] = combined;
        }
    }

    async sanitizeImage(el, sourceEl, measureEl) {
        const unmodifiedSrc = getImageSrc(el)?.trimStart();
        await Promise.all(this.trigger("on_save_pending_images_handlers", el, sourceEl));
        let src = getImageSrc(el)?.trimStart();
        let data = { ...el.dataset, ...(await loadImageInfo(el)) };
        let attachmentId = this.getMainAttachmentId(data);
        if (!src || (src === PLACEHOLDER_IMAGE && attachmentId)) {
            this.updateImageSource(el, unmodifiedSrc);
            this.updateImageSource(sourceEl, unmodifiedSrc);
            throw new EmailImageAttachmentCreationError(
                `The image could not be saved. ${getDisplayUrl(unmodifiedSrc)}`
            );
        }
        if (!attachmentId) {
            // If there is no attachment, reset the image source and attempt
            // to create one.
            this.updateImageSource(el, unmodifiedSrc);
            this.updateImageSource(sourceEl, unmodifiedSrc);
            let isShape;
            let attachmentSrc = unmodifiedSrc;
            if (data.shape && data.originalSrc) {
                isShape = true;
                attachmentSrc = data.originalSrc;
            }
            const dataUrl = await this.urlToDataUrl(attachmentSrc);
            let attachment;
            if (dataUrl) {
                attachment = await this.convertImageDataToEditorAttachment(dataUrl);
            }
            if (!attachment || !attachment.image_src) {
                throw new EmailImageAttachmentCreationError(
                    `The image could not be saved. ${getDisplayUrl(unmodifiedSrc)}`
                );
            }
            this.updateImageData(el, attachment);
            this.updateImageData(sourceEl, attachment);
            if (isShape) {
                const updatedSrc = getImageSrc(sourceEl)?.trimStart();
                const updateAttributes = await this.dependencies.imagePostProcess.processImage({
                    img: sourceEl,
                    newDataset: { shape: data.shape },
                });
                updateAttributes();
                const processedSrc = getImageSrc(sourceEl)?.trimStart();
                if (processedSrc && sourceEl.classList.contains("o_modified_image_to_save")) {
                    this.updateImageSource(el, processedSrc);
                    sourceEl.classList.add("o_modified_image_to_save");
                    await Promise.all(
                        this.trigger("on_save_pending_images_handlers", el, sourceEl)
                    );
                    src = getImageSrc(el)?.trimStart();
                    if (!src || src === PLACEHOLDER_IMAGE) {
                        throw new EmailImageAttachmentCreationError(
                            `The image could not be saved. ${getDisplayUrl(processedSrc)}`
                        );
                    }
                } else if (updatedSrc !== processedSrc) {
                    this.updateImageSource(sourceEl, updatedSrc);
                    throw new InvalidEmailImageSourceError(
                        `The image could not be processed. ${getDisplayUrl(updatedSrc)}`
                    );
                }
            }
            src = getImageSrc(el)?.trimStart();
            data = { ...el.dataset, ...(await loadImageInfo(el)) };
            attachmentId = this.getMainAttachmentId(data);
        }
        this.measureUtils = await this.measureUtilsPromise;
        const mimetype = data.mimetype && data.mimetype !== "undefined" ? data.mimetype : undefined;
        const imageInfo = {
            mimetype,
            attachmentId,
        };
        if (el.nodeName === "IMG") {
            if (
                !mimetype ||
                FORBIDDEN_EMAIL_MIMETYPE.has(mimetype) ||
                el.dataset.emailImageSrc === PLACEHOLDER_IMAGE
            ) {
                return this.sanitizeImgElement(src, imageInfo, el, sourceEl, measureEl);
            }
        } else {
            return this.sanitizeBackgroundImage(src, imageInfo, el, sourceEl, measureEl);
        }
    }

    computeCoverGeometry(measureEl, naturalDimensions, targetDimensions) {
        const getNormalizedValue = (name) =>
            (parseFloat(this.measureUtils.getStylePropertyValue(measureEl, name)) || 0) / 100;
        const xPos = getNormalizedValue("background-position-x");
        const yPos = getNormalizedValue("background-position-y");
        const scale = Math.max(
            targetDimensions.width / naturalDimensions.width,
            targetDimensions.height / naturalDimensions.height
        );
        const width = naturalDimensions.width * scale;
        const height = naturalDimensions.height * scale;
        return {
            targetPosition: {
                x: (width - targetDimensions.width) * xPos,
                y: (height - targetDimensions.height) * yPos,
            },
            renderedDimensions: { width, height },
        };
    }

    /**
     * renderedDimensions may not be adequate relative to naturalDimensions:
     * - too small and it will result in a big loss of image quality
     * - too high and it will result in a bigger image with interpolated pixels (not useful)
     * This function scales output dimensions between boundaries according to that relation:
     * - lower boundary prevents generating a too low res filter on a low res image
     * - upper boundary prevents storing a big file when most of the quality is not perceptible
     */
    scaleDimensions(targetDimensions, naturalDimensions, renderedDimensions, targetPosition) {
        const scale = Math.min(
            naturalDimensions.width / renderedDimensions.width,
            naturalDimensions.height / renderedDimensions.height
        );
        let outputScale = Math.min(EMAIL_IMAGE_RESOLUTION_SCALING.max, scale);
        if (scale < 1) {
            // Bias towards 1 allowing to store interpolated source image pixels
            // for a better filter quality
            outputScale = Math.max(
                EMAIL_IMAGE_RESOLUTION_SCALING.min,
                Math.min((3 * scale) / 2, 1)
            );
        }
        Object.assign(renderedDimensions, normalizeDimensions(renderedDimensions, outputScale));
        Object.assign(targetDimensions, normalizeDimensions(targetDimensions, outputScale));
        Object.assign(targetPosition, normalizePosition(targetPosition, outputScale));
    }

    async sanitizeBackgroundImage(src, imageInfo, el, sourceEl, measureEl) {
        const { mimetype } = imageInfo;
        // TODO EGGMAIL: does not support repeat neither on the background, neither on the gradient
        const filterEl = measureEl.firstElementChild?.matches(".o_we_bg_filter")
            ? measureEl.firstElementChild
            : undefined;
        const targetDimensions = this.getMeasuredBackgroundDimensions(measureEl);
        const naturalDimensions = await this.getImageNaturalDimensions(src);
        if (mimetype === SVG_MIMETYPE || !naturalDimensions.width || !naturalDimensions.height) {
            // TODO EGGMAIL: scale SVGs higher than rendered dimensions for better quality?
            Object.assign(
                naturalDimensions,
                await this.computeSvgNaturalDimensions(src, targetDimensions)
            );
        }
        const { renderedDimensions, targetPosition } = this.computeCoverGeometry(
            measureEl,
            naturalDimensions,
            targetDimensions
        );
        this.scaleDimensions(
            targetDimensions,
            naturalDimensions,
            renderedDimensions,
            targetPosition
        );
        let filterData = undefined;
        if (filterEl) {
            filterData = {};
            if (filterEl.matches("[style*=background-image]")) {
                filterData.gradient = extractGradientData(
                    this.measureUtils.getStylePropertyValue(filterEl, "background-image")
                );
            } else if (
                filterEl.matches("[style*=background-color]") ||
                hasTextColorClass(filterEl, "backgroundColor")
            ) {
                filterData.color = this.measureUtils.getStylePropertyValue(
                    filterEl,
                    "background-color"
                );
            }
        }
        const checksum = await computeEmailImageChecksum(
            "background",
            src,
            mimetype,
            renderedDimensions,
            targetDimensions,
            targetPosition,
            filterData
        );
        if (sourceEl.dataset.emailImageSrc && checksum === sourceEl.dataset.emailImageChecksum) {
            return;
        }
        if (this.checksumCache.has(checksum)) {
            this.setEmailImage(this.checksumCache.get(checksum), checksum, el, sourceEl);
            return;
        }
        const imageData = await this.convertBackgroundToImageData(
            src,
            renderedDimensions,
            targetDimensions,
            targetPosition,
            filterData
        );
        const newSrc = await this.convertImageDataToEmailAttachmentSrc(imageData, imageInfo);
        this.setEmailImage(newSrc, checksum, el, sourceEl);
    }

    setEmailImage(src, checksum, el, sourceEl) {
        el.dataset.emailImageSrc = src;
        sourceEl.dataset.emailImageSrc = src;
        if (src === PLACEHOLDER_IMAGE) {
            delete el.dataset.emailImageChecksum;
            delete sourceEl.dataset.emailImageChecksum;
            return;
        }
        if (!this.checksumCache.has(checksum)) {
            this.checksumCache.set(checksum, src);
        }
        el.dataset.emailImageChecksum = checksum;
        sourceEl.dataset.emailImageChecksum = checksum;
    }

    convertSvgToImg(svg) {
        const svgString = new XMLSerializer().serializeToString(svg);
        const bytes = new TextEncoder().encode(svgString);
        const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join("");
        const base64 = btoa(binary);
        const src = `data:image/svg+xml;base64,${base64}`;
        const img = this.document.createElement("IMG");
        for (const name of svg.getAttributeNames()) {
            if (SVG_EXCLUSIVE_ATTRIBUTES.has(name)) {
                continue;
            }
            img.setAttribute(name, svg.getAttribute(name));
        }
        img.classList.add("o_b64_image_to_save");
        img.src = src;
        return img;
    }

    /**
     * Convert a `<svg>` to `<img>` with a b64 src, in the editor as well, to
     * properly manage the related attachment.
     */
    async sanitizeSvg(el) {
        const noideidData = this.nodeidMap.get(el.dataset.oeNodeid);
        const { sourceEl } = noideidData;
        const img = this.convertSvgToImg(el);
        el.after(img);
        el.remove();
        const sourceImg = img.cloneNode(true);
        sourceEl.after(sourceImg);
        sourceEl.remove();
        noideidData.sourceEl = sourceImg;
    }

    async sanitizeImgElement(src, imageInfo, el, sourceEl, measureEl) {
        const { mimetype } = imageInfo;
        const dimensions = await this.getImageNaturalDimensions(src);
        if (mimetype === SVG_MIMETYPE || !dimensions.width || !dimensions.height) {
            // TODO EGGMAIL: scale SVGs higher than rendered dimensions for better quality?
            const measuredDimensions = this.getMeasuredImageDimensions(measureEl);
            Object.assign(
                dimensions,
                await this.computeSvgNaturalDimensions(src, measuredDimensions)
            );
        }
        const checksum = await computeEmailImageChecksum("IMG", src, mimetype, dimensions);
        if (sourceEl.dataset.emailImageSrc && checksum === sourceEl.dataset.emailImageChecksum) {
            return;
        }
        if (this.checksumCache.has(checksum)) {
            this.setEmailImage(this.checksumCache.get(checksum), checksum, el, sourceEl);
            return;
        }
        const imageData = await this.convertImgToImageData(el, dimensions.width, dimensions.height);
        const newSrc = await this.convertImageDataToEmailAttachmentSrc(imageData, imageInfo);
        this.setEmailImage(newSrc, checksum, el, sourceEl);
    }

    forEachSvg(callback, editable) {
        const promises = [];
        for (const svg of selectElements(editable, "svg")) {
            promises.push(callback(svg));
        }
        return promises;
    }

    forEachImg(callback, editable) {
        const promises = [];
        for (const img of selectElements(editable, "img")) {
            promises.push(callback(img));
        }
        return promises;
    }

    forEachBackgroundImg(callback, editable) {
        const promises = [];
        for (const el of selectElements(editable, `[style*="background-image"]`)) {
            const parts = backgroundImageCssToParts(el.style.getPropertyValue("background-image"));
            if ("url" in parts) {
                promises.push(callback(el));
            }
        }
        return promises;
    }

    async getImageNaturalDimensions(src) {
        return loadImage(src).then((i) => ({
            width: i.naturalWidth,
            height: i.naturalHeight,
        }));
    }

    getMeasuredBackgroundDimensions(measureEl) {
        return this.measureUtils.getBoundingClientRect(measureEl);
    }

    getMeasuredImageDimensions(measureEl) {
        const { width, height } = this.measureUtils.getBoundingClientRect(measureEl);
        const style = this.measureUtils.getComputedStyle(measureEl);
        const getValue = (name) => parseCssValue(style.getPropertyValue(name)).number ?? 0;
        const horizontalValues = [
            "padding-left",
            "padding-right",
            "border-left-width",
            "border-right-width",
        ];
        const verticalValues = [
            "padding-top",
            "padding-bottom",
            "border-top-width",
            "border-bottom-width",
        ];
        const reduceSum = (accumulator, name) => accumulator + getValue(name);
        const horizontalExtras = horizontalValues.reduce(reduceSum, 0);
        const verticalExtras = verticalValues.reduce(reduceSum, 0);
        return {
            width: width - horizontalExtras,
            height: height - verticalExtras,
        };
    }
}

registry.category("mail-core-plugins").add(EmailImageFormatPlugin.id, EmailImageFormatPlugin);
