import { cropperDataFieldsWithAspectRatio, isGif } from "@html_editor/utils/image_processing";
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
        "builder-options",
    ];
    static shared = ["canHaveHoverEffect"];
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
            }),
            withSequence(ALIGNMENT_STYLE_PADDING, {
                template: "html_builder.ImageAndFaOption",
                selector: "span.fa, i.fa, img",
                exclude: "[data-oe-type='image'] > img, [data-oe-xpath]",
            }),
        ],
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            cropImage: {
                isApplied: ({ editingElement }) =>
                    cropperDataFieldsWithAspectRatio.some((field) => editingElement.dataset[field]),
                load: ({ editingElement: img }) =>
                    new Promise((resolve) => {
                        this.dependencies.imageCrop.openCropImage(img, {
                            onClose: resolve,
                            onSave: async (newDataset) => {
                                resolve(
                                    this.dependencies.imagePostProcess.processImage(img, newDataset)
                                );
                            },
                        });
                    }),
                apply: ({ loadResult: updateImageAttributes }) => {
                    updateImageAttributes?.();
                },
            },
            resetCrop: {
                load: async ({ editingElement: img }) => {
                    const newDataset = Object.fromEntries(
                        cropperDataFieldsWithAspectRatio.map((field) => [field, undefined])
                    );
                    return this.dependencies.imagePostProcess.processImage(img, newDataset);
                },
                apply: ({ loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                },
            },
            transformImage: {
                isApplied: ({ editingElement }) => editingElement.matches(`[style*="transform"]`),
                apply: () => {
                    this.dependencies.userCommand.getCommand("transformImage").run();
                },
            },
            resetTransformImage: {
                apply: ({ editingElement }) => {
                    editingElement.setAttribute(
                        "style",
                        (editingElement.getAttribute("style") || "").replace(
                            /[^;]*transform[\w:]*;?/g,
                            ""
                        )
                    );
                },
            },
            replaceMedia: {
                load: async ({ editingElement }) => {
                    let icon;
                    await this.dependencies.media.openMediaDialog({
                        node: editingElement,
                        save: (newIcon) => {
                            icon = newIcon;
                        },
                    });
                    return icon;
                },
                apply: ({ editingElement, loadResult: newImage }) => {
                    if (!newImage) {
                        return;
                    }
                    editingElement.replaceWith(newImage);
                    this.dependencies.history.addStep();
                    this.dependencies["builder-options"].updateContainers(newImage);
                },
            },
            setLink: {
                preview: false,
                apply: ({ editingElement }) => {
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
                },
                isApplied: ({ editingElement }) => {
                    const parentEl = searchSupportedParentLinkEl(editingElement);
                    return parentEl.tagName === "A";
                },
            },
            setUrl: {
                preview: false,
                apply: ({ editingElement, value }) => {
                    const linkEl = searchSupportedParentLinkEl(editingElement);
                    let url = value;
                    if (!url) {
                        // As long as there is no URL, the image is not considered a link.
                        linkEl.removeAttribute("href");
                        return;
                    }
                    if (
                        !url.startsWith("/") &&
                        !url.startsWith("#") &&
                        !/^([a-zA-Z]*.):.+$/gm.test(url)
                    ) {
                        // We permit every protocol (http:, https:, ftp:, mailto:,...).
                        // If none is explicitly specified, we assume it is a http.
                        url = "http://" + url;
                    }
                    linkEl.setAttribute("href", url);
                },
                getValue: ({ editingElement }) => {
                    const linkEl = searchSupportedParentLinkEl(editingElement);
                    return linkEl.getAttribute("href");
                },
            },
            setNewWindow: {
                preview: false,
                apply: ({ editingElement, value }) => {
                    const linkEl = searchSupportedParentLinkEl(editingElement);
                    linkEl.setAttribute("target", "_blank");
                },
                clean: ({ editingElement }) => {
                    const linkEl = searchSupportedParentLinkEl(editingElement);
                    linkEl.removeAttribute("target");
                },
                isApplied: ({ editingElement }) => {
                    const linkEl = searchSupportedParentLinkEl(editingElement);
                    return linkEl.getAttribute("target") === "_blank";
                },
            },

            alt: {
                getValue: ({ editingElement: imgEl }) => imgEl.alt,
                apply: ({ editingElement: imgEl, value }) => {
                    const trimmedValue = value.trim();
                    if (trimmedValue) {
                        imgEl.alt = trimmedValue;
                        if (imgEl.getAttribute("role") === "presentation") {
                            imgEl.removeAttribute("role");
                        }
                    } else {
                        imgEl.removeAttribute("alt");
                    }
                },
            },
        };
    }
    async canHaveHoverEffect(img) {
        return (
            img.tagName === "IMG" &&
            !this.isDeviceShape(img) &&
            !this.isAnimatedShape(img) &&
            this.isImageSupportedForShapes(img) &&
            !(await isImageCorsProtected(img))
        );
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
    isImageSupportedForShapes(img) {
        return img.dataset.originalId && isImageSupportedForProcessing(getMimetype(img));
    }
}
registry.category("website-plugins").add(ImageToolOptionPlugin.id, ImageToolOptionPlugin);

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
