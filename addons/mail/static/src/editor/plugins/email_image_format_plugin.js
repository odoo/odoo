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
import { usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { ATTACHMENT_PENDING_RECORD_ID } from "@html_editor/main/media/media_plugin";

const SVG_MIMETYPE = "image/svg+xml";
const WEBP_MIMETYPE = "image/webp";
const FORBIDDEN_EMAIL_MIMETYPE = new Set([SVG_MIMETYPE, WEBP_MIMETYPE]);
const SVG_EXCLUSIVE_ATTRIBUTES = new Set(["viewBox", "preserveAspectRatio", "x", "y"]);
const PLACEHOLDER_IMAGE = "/html_editor/static/src/img/placeholder_thumbnail.png";
const RESOLUTION_SCALING_RANGE = { min: 0.5, max: 2 };
const SMALL_SVG_THRESHOLD = 150;

export class AggregateEmailImageError extends AggregateError {
    name = this.constructor.name;
}
export class EmailImageError extends Error {
    name = this.constructor.name;
}
class InvalidSourceEmailImageError extends EmailImageError {}
class AttachmentCreationEmailImageError extends EmailImageError {}
class UncleanOriginEmailImageError extends EmailImageError {}

function getDisplaySrc(src) {
    if (!src) {
        src = "";
    }
    src = typeof src === "string" ? src : src.toString();
    return `${src.substring(0, 50)}${src.length > 50 ? "..." : ""}`;
}

export class EmailImageFormatPlugin extends Plugin {
    static id = "emailImageFormat";
    static dependencies = ["imagePostProcess", "imageSave"];
    static shared = ["sanitizeImages", "setImageIdentity"];
    static defaultConfig = {
        // PNG is the default image format to preserve transparency.
        defaultImageMimetype: "image/png",
    };
    resources = {
        system_attributes: ["data-oe-nodeid"],
        on_media_added_handlers: ({ newMediaEl }) => this.resetEmailImageAttributes(newMediaEl),
        on_media_replaced_handlers: ({ newMediaEl }) => this.resetEmailImageAttributes(newMediaEl),
        on_image_updated_handlers: ({ imageEl }) => this.resetEmailImageAttributes(imageEl),
        on_image_saved_handlers: ({ imageEl }) => this.resetEmailImageAttributes(imageEl),
    };

    setup() {
        this.elToNodeid = new WeakMap();
        this.initializeChecksumCache();
        this.notification = usePlugin(NotificationPlugin);
        if (!this.config.measureReference) {
            throw new Error("This Plugin requires `measureReference` from `useEmailHtmlConverter`");
        }
    }

    /**
     * Both attachmentId and originalId (eg from a dataset) can refer to an
     * attachment related to a given image.
     * image_processing:loadImageInfo original_id refers to
     * ir.attachment.original_id which is the unmodified original attachment id,
     * so it's the one used if available, but some images might only have
     * attachmentId (e.g. add_url images using a redirect src), or none.
     */
    getMainAttachmentId(info) {
        return info.originalId || info.attachmentId;
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
                } else if (el.matches("img")) {
                    // TODO EGGMAIL: investigate image_save_plugin and
                    // make saveB64Image support background images too.
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

    setupMeasureClone(editableClone) {
        const measureClone = editableClone.cloneNode(true);
        const setMeasureEl = (el) => (this.nodeidMap.get(el.dataset.oeNodeid).measureEl = el);
        this.forEachImg(setMeasureEl, measureClone);
        this.forEachBackgroundImg(setMeasureEl, measureClone);
        const measureFragment = this.document.createDocumentFragment();
        measureFragment.replaceChildren(...childNodes(measureClone));
        this.measureUtilsPromise = this.config.measureReference(measureFragment);
        this.measureUtils = undefined;
    }

    /**
     * Ensure that every restricted image/background-image format (SVG/WEBP) is
     * converted to a mail-supported equivalent (PNG).
     */
    async sanitizeImages(editableClone) {
        this.forEachSvg((svg) => this.sanitizeSvg(svg), editableClone);
        this.setupMeasureClone(editableClone);

        const promises = [];
        const sanitizeImage = (el) => {
            const noideidData = this.nodeidMap.get(el.dataset.oeNodeid);
            // - el is part of the clone used by the html_field to compute the content to save in DB
            // - sourceEl is part of the editable currently used in the editor
            // - measureEl is a clone of the content to save put inside an iframe constrained
            //   with the final email dimensions and stylesheets (to perform measurements)
            const { sourceEl, measureEl } = noideidData;
            return this.sanitizeImage(el, sourceEl, measureEl).catch((reason) => {
                if (!(reason instanceof UncleanOriginEmailImageError)) {
                    // Keep no CORS / different domain images as is (no placeholder)
                    this.setEmailImage(PLACEHOLDER_IMAGE, undefined, el, sourceEl);
                }
                throw reason;
            });
        };
        promises.push(...this.forEachImg(sanitizeImage, editableClone));
        promises.push(...this.forEachBackgroundImg(sanitizeImage, editableClone));

        // Cleanup data-oe-nodeid from the editable and the clone to save
        this.cleanupImageIdentity(editableClone);
        this.cleanupImageIdentity(this.editable);

        const results = await Promise.allSettled(promises);
        const errors = [];
        const uncleanOriginErrors = [];
        let containsMiscErrors = false;
        for (const result of results) {
            if (result.status !== "rejected") {
                continue;
            }
            if (result.reason instanceof UncleanOriginEmailImageError) {
                uncleanOriginErrors.push(result.reason);
            } else {
                errors.push(result.reason);
            }
            if (!(result.reason instanceof EmailImageError)) {
                containsMiscErrors = true;
            }
        }
        if (uncleanOriginErrors.length > 0) {
            // Assume no CORS / different domain images are valid,
            // because they can't be processed anyways. These errors are not
            // thrown.
            // TODO EGGMAIL: make the server download the image to
            // create a data attachment and try to process it.
            this.notification.add(
                _t(
                    "Some images are hosted on an external domain, their reliability for emails can not be guaranteed. Upload them from your device if possible."
                ),
                {
                    type: "danger",
                    sticky: true,
                }
            );
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

    canvasToDataUrl(canvas, src) {
        try {
            return canvas.toDataURL(this.config.defaultImageMimetype);
        } catch {
            this.throwNoCORSError(src);
        }
    }

    async convertImgToImageData(img, width, height) {
        const { canvas, ctx } = await this.prepare2DCanvasForImg(img, width, height);
        ctx.drawImage(img, 0, 0, width, height);
        return this.canvasToDataUrl(canvas, img.src);
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
        return this.canvasToDataUrl(canvas, src);
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

    getRecordInfo(element) {
        const getClosestSavable = (el) => {
            for (const provider of this.getResource("closest_savable_providers")) {
                const value = provider(el);
                if (value) {
                    return value;
                }
            }
        };
        const editableEl = getClosestSavable(element);
        return this.config.getRecordInfo ? this.config.getRecordInfo(editableEl) : {};
    }

    throwFetchError(src) {
        throw new InvalidSourceEmailImageError(
            `The image could not be fetched. ${getDisplaySrc(src)}`
        );
    }

    throwCreateAttachmentError(src) {
        throw new AttachmentCreationEmailImageError(
            `The image could not be saved. ${getDisplaySrc(src)}`
        );
    }

    throwNoCORSError(src) {
        throw new UncleanOriginEmailImageError(
            `The image loaded successfully but couldn't be fetched, CORS headers are probably missing. ${getDisplaySrc(
                src
            )}`
        );
    }

    throwProcessImageError(src) {
        throw new InvalidSourceEmailImageError(
            `The image could not be processed. ${getDisplaySrc(src)}`
        );
    }

    async fetchImageUrl(url) {
        let response;
        try {
            response = await fetch(url);
        } catch {
            await loadImage(url).then(
                () => this.throwNoCORSError(url),
                () => this.throwFetchError(url)
            );
        }
        if (!response.ok) {
            this.throwFetchError(url);
        }
        return response;
    }

    async getSvgIntrinsicInfo(svgUrl) {
        const response = await this.fetchImageUrl(svgUrl);
        const text = await response.text();
        const doc = new DOMParser().parseFromString(text, "image/svg+xml");
        const svg = doc.documentElement;
        const viewBox = svg.getAttribute("viewBox");
        const width = svg.getAttribute("width") ?? "";
        const height = svg.getAttribute("height") ?? "";
        const parsedWidth = parseCssValue(width);
        const parsedHeight = parseCssValue(height);
        const output = {};
        if ((parsedWidth.unit === "px" || parsedWidth.unit === null) && parsedWidth.number > 0) {
            output.width = parsedWidth.number;
        }
        if ((parsedHeight.unit === "px" || parsedHeight.unit === null) && parsedHeight.number > 0) {
            output.height = parsedHeight.number;
        }
        if (viewBox) {
            const [, , vbWidth, vbHeight] = viewBox
                .trim()
                .split(/[\s,]+/)
                .map(Number);

            if (vbWidth > 0 && vbHeight > 0) {
                output.aspectRatio = vbWidth / vbHeight;
            }
        }
        if (
            output.aspectRatio === undefined &&
            parsedWidth.number > 0 &&
            parsedHeight.number > 0 &&
            parsedWidth.unit === parsedHeight.unit
        ) {
            const ratioWidth = parseFloat(width);
            const ratioHeight = parseFloat(height);
            if (ratioWidth > 0 && ratioHeight > 0) {
                output.aspectRatio = ratioWidth / ratioHeight;
            }
        }
        if (Object.keys(output).length === 0) {
            return output;
        }
        if ("aspectRatio" in output) {
            if ("width" in output && !("height" in output)) {
                output.height = output.width / output.aspectRatio;
            } else if ("height" in output && !("width" in output)) {
                output.width = output.height * output.aspectRatio;
            }
        }
        return output;
    }

    async computeSvgIntrinsicDimensions(src, measuredDimensions) {
        const intrinsicInfo = await this.getSvgIntrinsicInfo(src);
        if (intrinsicInfo.width && intrinsicInfo.height) {
            return intrinsicInfo;
        }
        const { aspectRatio } = intrinsicInfo;
        const dimensions = {};
        let { width, height } = measuredDimensions;
        // For small svg without intrinsic dimensions, render at increased
        // measured resolution
        const resolutionFactor =
            width < SMALL_SVG_THRESHOLD && height < SMALL_SVG_THRESHOLD
                ? RESOLUTION_SCALING_RANGE.max
                : 1;
        width *= resolutionFactor;
        height *= resolutionFactor;
        // For SVG images, render at measured dimensions since their
        // resolution is dynamic, and they don't necessarily have
        // natural dimensions nor are they relevant.
        dimensions.width = width;
        dimensions.height = height;
        if (aspectRatio !== undefined) {
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
            mimetype: attachment.mimetype,
            originalId: attachment.id,
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
        await this.dependencies.imageSave.savePendingImagesInClone(el, sourceEl);
        let src = getImageSrc(el)?.trimStart();
        let data = { ...el.dataset, ...(await loadImageInfo(el)) };
        let attachmentId = this.getMainAttachmentId(data);
        if (!src || (src === PLACEHOLDER_IMAGE && attachmentId)) {
            this.updateImageSource(el, unmodifiedSrc);
            this.updateImageSource(sourceEl, unmodifiedSrc);
            this.throwCreateAttachmentError(unmodifiedSrc);
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
                this.throwCreateAttachmentError(unmodifiedSrc);
            }
            this.updateImageData(el, attachment);
            this.updateImageData(sourceEl, attachment);
            if (!this.getRecordInfo(this.editable).resId) {
                // TODO EGGMAIL: investigate how to use saveB64Image in this
                // context and simplify the feature around ATTACHMENT_PENDING_RECORD_ID
                // (badly scoped service, no handling of background images, uses a
                // class in the html value instead of directly interacting with the
                // service, ...)
                sourceEl.dataset.attachmentId = attachment.id;
                sourceEl.classList.add(ATTACHMENT_PENDING_RECORD_ID);
            }
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
                    await this.dependencies.imageSave.savePendingImagesInClone(el, sourceEl);
                    src = getImageSrc(el)?.trimStart();
                    if (!src || src === PLACEHOLDER_IMAGE) {
                        this.throwCreateAttachmentError(processedSrc);
                    }
                } else if (updatedSrc !== processedSrc) {
                    this.updateImageSource(sourceEl, updatedSrc);
                    this.throwProcessImageError(updatedSrc);
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
            originalId: attachmentId,
        };
        if (el.nodeName === "IMG") {
            if (
                !mimetype ||
                FORBIDDEN_EMAIL_MIMETYPE.has(mimetype) ||
                el.dataset.emailImageSrc === PLACEHOLDER_IMAGE
            ) {
                return this.sanitizeImgElement(src, imageInfo, el, sourceEl, measureEl);
            } else {
                // Failsafe to remove potentially obsolete values (they should
                // have been cleaned prior to this step using editor resources).
                this.resetEmailImageAttributes(el);
                this.resetEmailImageAttributes(sourceEl);
            }
        } else {
            return this.sanitizeBackgroundImage(src, imageInfo, el, sourceEl, measureEl);
        }
    }

    computeCoverGeometry(measureEl, naturalDimensions, targetDimensions) {
        const getNormalizedBackgroundPositionValue = (name) => {
            const backgroundPosition = parseCssValue(
                this.measureUtils.getStylePropertyValue(measureEl, name)
            );
            if (backgroundPosition.unit !== "%") {
                // TODO EGGMAIL: to adjust if non-percentage values should
                // be supported.
                return 0;
            }
            return (parseFloat(backgroundPosition.number) || 0) / 100;
        };
        const xPos = getNormalizedBackgroundPositionValue("background-position-x");
        const yPos = getNormalizedBackgroundPositionValue("background-position-y");
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
        let outputScale = Math.min(RESOLUTION_SCALING_RANGE.max, scale);
        if (scale < 1) {
            // Bias towards 1 allowing to store interpolated source image pixels
            // for a better filter quality
            outputScale = Math.max(RESOLUTION_SCALING_RANGE.min, Math.min((3 * scale) / 2, 1));
        }
        Object.assign(renderedDimensions, normalizeDimensions(renderedDimensions, outputScale));
        Object.assign(targetDimensions, normalizeDimensions(targetDimensions, outputScale));
        Object.assign(targetPosition, normalizePosition(targetPosition, outputScale));
    }

    async sanitizeBackgroundImage(src, imageInfo, el, sourceEl, measureEl) {
        const { mimetype } = imageInfo;
        // TODO EGGMAIL: does not support repeat neither on the background, neither on the gradient;
        // Remove the editor option or adjust this code.
        const filterEl = measureEl.firstElementChild?.matches(".o_we_bg_filter")
            ? measureEl.firstElementChild
            : undefined;
        const targetDimensions = this.getMeasuredBackgroundDimensions(measureEl);
        const naturalDimensions = await this.getImageNaturalDimensions(src);
        if (mimetype === SVG_MIMETYPE || !naturalDimensions.width || !naturalDimensions.height) {
            Object.assign(
                naturalDimensions,
                await this.computeSvgIntrinsicDimensions(src, targetDimensions)
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

    resetEmailImageAttributes(el) {
        delete el.dataset.emailImageChecksum;
        delete el.dataset.emailImageSrc;
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
            const measuredDimensions = this.getMeasuredImageDimensions(measureEl);
            Object.assign(
                dimensions,
                await this.computeSvgIntrinsicDimensions(src, measuredDimensions)
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
