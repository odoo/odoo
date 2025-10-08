import { Plugin } from "@html_editor/plugin";
import {
    backgroundImageCssToParts,
    backgroundImagePartsToCss,
    getImageSrc,
} from "@html_editor/utils/image";
import { loadImage, loadImageInfo } from "@html_editor/utils/image_processing";
import { registry } from "@web/core/registry";

const EMAIL_RESTRICTED_IMAGE_MIMETYPES = ["image/svg+xml", "image/webp"];
const EMAIL_RESTRICTED_IMAGE_MIMETYPES_SET = new Set(EMAIL_RESTRICTED_IMAGE_MIMETYPES);

export class ImageFormatPlugin extends Plugin {
    static id = "mail.ImageFormatPlugin";
    static dependencies = ["imagePostProcess", "imageSave"];
    static shared = ["sanitizeImages"];
    static defaultConfig = {
        // TODO EGGMAIL: if transparency usage can be detected, prefer JPEG over PNG
        // currently there is no transparency detection logic, so PNG is used by default.
        // PNG is the default image format to preserve transparency.
        defaultImageMimetype: "image/png",
    };

    setup() {
        this.imgNodes = new WeakMap();
        this.bgImgNodes = new WeakMap();
        this.textEncoder = new TextEncoder();
        this.textDecoder = new TextDecoder();
    }

    /**
     * Ensure that every restricted image/background-image format (SVG/WEBP) is
     * converted to a mail-supported equivalent (PNG).
     */
    async sanitizeImages() {
        const promises = [];
        promises.push(...this.forEachSvg((svg) => this.sanitizeSvg(svg)));
        promises.push(...this.forEachImg((img) => this.sanitizeImage(img)));
        promises.push(...this.forEachBackgroundImg((el) => this.sanitizeImage(el)));
        await Promise.all(promises);
        await this.dependencies.imageSave.savePendingImages();
        // Register images in a cache, to avoid handling unchanged src.
        this.forEachImg((img) => {
            const src = getImageSrc(img);
            this.imgNodes.set(img, src);
        });
        this.forEachBackgroundImg((el) => {
            const src = getImageSrc(el);
            this.bgImgNodes.set(el, src);
        });
    }

    convertSvgHTMLToB64(svgHTML) {
        return this.textDecoder.decode(this.textEncoder.encode(svgHTML));
    }

    /**
     * Convert a `<svg>` to `<img>` with a b64 src.
     */
    async sanitizeSvg(el) {
        const imageData = this.convertSvgHTMLToB64(el.outerHTML);
        const img = this.document.createElement("IMG");
        const attachment = await this.convertImageDataToAttachment(img, imageData);
        if (attachment) {
            el.after(img);
            el.remove();
        }
        return this.sanitizeImage(img);
    }

    async convertImageDataToAttachment(el, imageData) {
        const { resModel, resId } = this.getRecordInfo(el);
        const attachment = await this.dependencies.imageSave.createAttachment({
            el,
            imageData,
            resModel,
            resId,
        });
        if (!attachment) {
            return;
        }
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
        Object.assign(el.dataset, {
            fileName: attachment.name,
            mimetype: attachment.mimetype,
            mimetypeBeforeConversion: attachment.mimetype,
            originalId: attachment.id,
            originalSrc: attachment.image_src,
        });
        if (el.matches("img")) {
            el.src = src;
        } else {
            const parts = backgroundImageCssToParts(el.style["background-image"]);
            parts.url = `url('${src}')`;
            const combined = backgroundImagePartsToCss(parts);
            el.style["background-image"] = combined;
        }
        return attachment;
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

    async sanitizeImage(el) {
        const src = getImageSrc(el).trimStart();
        if (!src) {
            return;
        }
        const data = { ...el.dataset, ...(await loadImageInfo(el)) };
        if (!data.mimetypeBeforeConversion || !data.originalSrc) {
            // If the SVG/WEBP data image was not related to an attachment,
            // attempt to create one.
            const DATA_SVG = "data:image/svg+xml";
            if (src.startsWith(`${DATA_SVG},`)) {
                // Create an attachment for a plain XML SVG data src.
                const svgHTML = src.split(`${DATA_SVG},`)[1];
                const attachment = await this.convertImageDataToAttachment(
                    el,
                    this.convertSvgHTMLToB64(svgHTML)
                );
                if (attachment) {
                    Object.assign(data, el.dataset);
                }
            } else if (
                EMAIL_RESTRICTED_IMAGE_MIMETYPES.some((mimetype) =>
                    src.startsWith(`data:${mimetype};base64,`)
                )
            ) {
                // Create an attachment for a b64 SVG or WEBP data src.
                const imageData = src.split("base64,")[1];
                const attachment = await this.convertImageDataToAttachment(el, imageData);
                if (attachment) {
                    Object.assign(data, el.dataset);
                }
            }
        }
        if (!data.mimetypeBeforeConversion || !data.originalSrc) {
            // No attachment is currently available for the image.
            return;
        }
        if (
            !EMAIL_RESTRICTED_IMAGE_MIMETYPES_SET.has(data.mimetypeBeforeConversion) ||
            (el.dataset.formatMimetype &&
                !EMAIL_RESTRICTED_IMAGE_MIMETYPES_SET.has(el.dataset.formatMimetype))
        ) {
            return;
        }
        const resizeWidth = await this.getImageWidth(data.originalSrc, data.width);
        const updateImageAttributes = await this.dependencies.imagePostProcess.processImage({
            img: el,
            newDataset: {
                resizeWidth,
                formatMimetype: this.config.defaultImageMimetype,
            },
        });
        return updateImageAttributes();
    }

    forEachSvg(callback) {
        const promises = [];
        for (const svg of this.editable.querySelectorAll("svg")) {
            promises.push(callback(svg));
        }
        return promises;
    }

    forEachImg(callback) {
        const promises = [];
        for (const img of this.editable.querySelectorAll("img")) {
            if (this.imgNodes.has(img) && this.imgNodes.get(img) === img.src) {
                continue;
            }
            promises.push(callback(img));
        }
        return promises;
    }

    forEachBackgroundImg(callback) {
        const promises = [];
        for (const el of this.editable.querySelectorAll(`[style*="background-image"]`)) {
            const { url } = backgroundImageCssToParts(el.style.getProperty("background-image"));
            if (this.bgImgNodes.has(el) && this.bgImgNodes.get(el) === url) {
                continue;
            }
            promises.push(callback(el));
        }
        return promises;
    }

    async getImageWidth(originalSrc, width) {
        const getNaturalWidth = () => loadImage(originalSrc).then((i) => i.naturalWidth);
        return width ? Math.round(width) : Math.round(await getNaturalWidth());
    }
}

registry.category("mail-core-plugins").add(ImageFormatPlugin.id, ImageFormatPlugin);
