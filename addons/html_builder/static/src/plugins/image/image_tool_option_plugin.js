import {
    cropperDataFieldsWithAspectRatio,
    isGif,
    loadImage,
    loadImageInfo,
} from "@html_editor/utils/image_processing";
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { ImageToolOption } from "./image_tool_option";
import { isImageCorsProtected, getMimetype } from "@html_editor/utils/image";
import { withSequence } from "@html_editor/utils/resource";
import {
    REPLACE_MEDIA,
    IMAGE_TOOL,
    ALIGNMENT_STYLE_PADDING,
} from "@html_builder/utils/option_sequence";
import { ReplaceMediaOption, searchSupportedParentLinkEl } from "./replace_media_option";
import { computeMaxDisplayWidth } from "@html_builder/plugins/image/image_format_option";
import { BuilderAction } from "@html_builder/core/builder_action";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { isCSSColor } from "@web/core/utils/colors";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";

export const REPLACE_MEDIA_SELECTOR = "img, .media_iframe_video, span.fa, i.fa";
export const REPLACE_MEDIA_EXCLUDE =
    "[data-oe-xpath], a[href^='/website/social/'] > i.fa, a[class*='s_share_'] > i.fa";

class ImageToolOptionPlugin extends Plugin {
    static id = "imageToolOption";
    static dependencies = [
        "history",
        "userCommand",
        "imagePostProcess",
        "imageCrop",
        "media",
        "builderOptions",
    ];
    static shared = ["getCSSColorValue"];
    resources = {
        builder_options: [
            withSequence(REPLACE_MEDIA, {
                OptionComponent: ReplaceMediaOption,
                selector: REPLACE_MEDIA_SELECTOR,
                exclude: REPLACE_MEDIA_EXCLUDE,
                name: "replaceMediaOption",
            }),
            withSequence(IMAGE_TOOL, {
                OptionComponent: ImageToolOption,
                selector: "img",
                exclude: "[data-oe-type='image'] > img",
            }),
            withSequence(ALIGNMENT_STYLE_PADDING, {
                template: "html_builder.ImageAndFaOption",
                selector: "span.fa, i.fa, img",
                exclude: "[data-oe-type='image'] > img, [data-oe-xpath]",
            }),
        ],
        builder_actions: {
            CropImageAction,
            ResetCropAction,
            ReplaceMediaAction,
            SetLinkAction,
            SetUrlAction,
            SetNewWindowAction,
            AltAction,
        },
        on_media_dialog_saved_handlers: async (elements, { node }) => {
            for (const image of elements) {
                if (image && image.tagName === "IMG") {
                    const updateImageAttributes =
                        await this.dependencies.imagePostProcess.processImage({
                            img: image,
                            newDataset: {
                                formatMimetype: "image/webp",
                            },
                            // TODO Using a callback is currently needed to avoid
                            // the extra RPC that would occur if loadImageInfo was
                            // called before processImage as well. This flow can be
                            // simplified if image infos are somehow cached.
                            onImageInfoLoaded: async (dataset) => {
                                if (!dataset.originalSrc || !dataset.originalId) {
                                    return true;
                                }
                                const original = await loadImage(dataset.originalSrc);
                                const maxWidth = dataset.width
                                    ? image.naturalWidth
                                    : original.naturalWidth;
                                const optimizedWidth = Math.min(
                                    maxWidth,
                                    computeMaxDisplayWidth(node || this.editable)
                                );
                                if (
                                    !["image/gif", "image/svg+xml"].includes(
                                        dataset.mimetypeBeforeConversion
                                    )
                                ) {
                                    // Convert to recommended format and width.
                                    dataset.resizeWidth = optimizedWidth;
                                } else if (
                                    dataset.shape &&
                                    dataset.mimetypeBeforeConversion !== "image/gif"
                                ) {
                                    dataset.resizeWidth = optimizedWidth;
                                } else {
                                    return true;
                                }
                            },
                        });
                    updateImageAttributes();
                }
            }
        },
        hover_effect_allowed_predicates: (el) => this.canHaveHoverEffect(el),
        // TODO Remove in master.
        normalize_handlers: this.migrateImages.bind(this),
    };
    setup() {
        this.htmlStyle = getHtmlStyle(this.document);
    }

    async canHaveHoverEffect(img) {
        const getDataset = async () => Object.assign({}, img.dataset, await loadImageInfo(img));
        return img.tagName === "IMG"
            ? !this.isDeviceShape(img) &&
                  !this.isAnimatedShape(img) &&
                  this.isImageSupportedForShapes(img, await getDataset()) &&
                  !(await isImageCorsProtected(img))
            : null;
    }
    isDeviceShape(img) {
        const shapeName = img.dataset.shape;
        if (!shapeName) {
            return false;
        }
        const shapeCategory = shapeName.split("/")[1];
        return shapeCategory === "devices";
    }
    isAnimatedShape(img) {
        // todo: to implement while implementing the animated shapes
        return false;
    }
    isImageSupportedForShapes(img, dataset = img.dataset) {
        // todo: The hover effect code should probably be define somewhere else.
        const isHoverEffect = !!dataset["hoverEffect"];
        return (
            isHoverEffect ||
            (dataset.originalId && isImageSupportedForProcessing(getMimetype(img, dataset)))
        );
    }
    // TODO Remove in master.
    migrateImages(rootEl) {
        for (const el of selectElements(
            rootEl,
            "img[data-original-id]:not([data-attachment-id]), .oe_img_bg[data-original-id]:not([data-attachment-id])"
        )) {
            el.dataset.attachmentId = el.dataset.originalId;
        }
        for (const el of selectElements(
            rootEl,
            "img[data-original-mimetype]:not([data-format-mimetype]), .oe_img_bg[data-original-mimetype]:not([data-format-mimetype])"
        )) {
            el.dataset.formatMimetype = el.dataset.originalMimetype;
            delete el.dataset.originalMimetype;
        }
    }
    /**
     * Gets the CSS value of a color variable name.
     *
     * @param {string} color
     * @returns {string}
     */
    getCSSColorValue(color) {
        if (!color || isCSSColor(color)) {
            return color;
        }
        return getCSSVariableValue(color, this.htmlStyle);
    }
}

export class CropImageAction extends BuilderAction {
    static id = "cropImage";
    static dependencies = ["imageCrop", "imagePostProcess"];
    isApplied({ editingElement }) {
        return cropperDataFieldsWithAspectRatio.some((field) => editingElement.dataset[field]);
    }
    load({ editingElement: img }) {
        return new Promise((resolve) => {
            this.dependencies.imageCrop.openCropImage(img, {
                onClose: resolve,
                onSave: async (newDataset) => {
                    resolve(this.dependencies.imagePostProcess.processImage({ img, newDataset }));
                },
            });
        });
    }
    apply({ loadResult: updateImageAttributes }) {
        updateImageAttributes?.();
    }
}

export class ResetCropAction extends BuilderAction {
    static id = "resetCrop";
    static dependencies = ["imagePostProcess"];
    async load({ editingElement: img }) {
        const newDataset = Object.fromEntries(
            cropperDataFieldsWithAspectRatio.map((field) => [field, undefined])
        );
        return this.dependencies.imagePostProcess.processImage({ img, newDataset });
    }
    apply({ loadResult: updateImageAttributes }) {
        updateImageAttributes();
    }
}

export class ReplaceMediaAction extends BuilderAction {
    static id = "replaceMedia";
    static dependencies = ["media_website"];
    async apply({ editingElement: mediaEl }) {
        await this.dependencies["media_website"].replaceMedia(mediaEl);
    }
}
export class SetLinkAction extends BuilderAction {
    static id = "setLink";
    setup() {
        this.preview = false;
    }
    apply({ editingElement }) {
        const parentEl = searchSupportedParentLinkEl(editingElement);
        if (parentEl.tagName !== "A") {
            const wrapperEl = document.createElement("a");
            editingElement.after(wrapperEl);
            wrapperEl.appendChild(editingElement);
        } else {
            const fragment = document.createDocumentFragment();
            fragment.append(...parentEl.childNodes);
            parentEl.replaceWith(fragment);
        }
    }
    isApplied({ editingElement }) {
        const parentEl = searchSupportedParentLinkEl(editingElement);
        return parentEl.tagName === "A";
    }
}

export class SetUrlAction extends BuilderAction {
    static id = "setUrl";
    setup() {
        this.preview = false;
    }
    apply({ editingElement, value }) {
        const linkEl = searchSupportedParentLinkEl(editingElement);
        let url = value;
        if (!url) {
            // As long as there is no URL, the image is not considered a link.
            linkEl.removeAttribute("href");
            return;
        }
        if (!url.startsWith("/") && !url.startsWith("#") && !/^([a-zA-Z]*.):.+$/gm.test(url)) {
            // We permit every protocol (http:, https:, ftp:, mailto:,...).
            // If none is explicitly specified, we assume it is a http.
            url = "http://" + url;
        }
        linkEl.setAttribute("href", url);
    }
    getValue({ editingElement }) {
        const linkEl = searchSupportedParentLinkEl(editingElement);
        return linkEl.getAttribute("href");
    }
}

export class SetNewWindowAction extends BuilderAction {
    static id = "setNewWindow";
    setup() {
        this.preview = false;
    }
    apply({ editingElement, value }) {
        const linkEl = searchSupportedParentLinkEl(editingElement);
        linkEl.setAttribute("target", "_blank");
    }
    clean({ editingElement }) {
        const linkEl = searchSupportedParentLinkEl(editingElement);
        linkEl.removeAttribute("target");
    }
    isApplied({ editingElement }) {
        const linkEl = searchSupportedParentLinkEl(editingElement);
        return linkEl.getAttribute("target") === "_blank";
    }
}

export class AltAction extends BuilderAction {
    static id = "alt";
    getValue({ editingElement: imgEl }) {
        return imgEl.alt;
    }
    apply({ editingElement: imgEl, value }) {
        const trimmedValue = value.trim();
        if (trimmedValue) {
            imgEl.alt = trimmedValue;
            if (imgEl.getAttribute("role") === "presentation") {
                imgEl.removeAttribute("role");
            }
        } else {
            imgEl.removeAttribute("alt");
        }
    }
}

registry.category("builder-plugins").add(ImageToolOptionPlugin.id, ImageToolOptionPlugin);

/**
 * @param {String} mimetype
 * @param {Boolean} [strict=false] if true, even partially supported images (GIFs)
 *     won't be accepted.
 * @returns {Boolean}
 */
function isImageSupportedForProcessing(mimetype, strict = false) {
    if (isGif(mimetype)) {
        return !strict;
    }
    return ["image/jpeg", "image/png", "image/webp"].includes(mimetype);
}
