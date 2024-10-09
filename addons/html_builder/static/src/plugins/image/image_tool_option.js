import {
    cropperAspectRatios,
    getMimetype,
    processImageCrop,
} from "@html_editor/main/media/image_crop";
import {
    activateCropper,
    applyModifications,
    isGif,
    loadImage,
} from "@html_editor/utils/image_processing";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { defaultBuilderComponents } from "../../core/default_builder_components";
import { AddElementOption } from "../add_element_option";
import { SpacingOption } from "../spacing_option";
import { Plugin } from "@html_editor/plugin";
import { useIsActiveItem } from "../../core/building_blocks/utils";
import { isImageCorsProtected } from "@html_builder/utils/utils_css";
import { ImageShapeOption } from "./image_shape_option";
import { getImageMimetype } from "./image_helpers";

class ImageToolOptionPlugin extends Plugin {
    static id = "ImageToolOption";
    static dependencies = ["history", "userCommand"];
    resources = {
        builder_options: [
            {
                OptionComponent: ImageToolOption,
                selector: "img",
            },
            {
                template: "html_builder.ImageAndFaOption",
                selector: "span.fa, i.fa, img",
                exclude: "[data-oe-type='image'] > img, [data-oe-xpath]",
            },
        ],
        builder_actions: this.getActions(),
        is_hoverable_predicates: (el) => {
            if (el.tagName !== "IMG") {
                return true;
            }
            return this.canHaveHoverEffect(el);
        },
    };
    getActions() {
        return {
            cropImage: {
                isApplied: ({ editingElement }) =>
                    editingElement.classList.contains("o_we_image_cropped"),
                apply: () => {
                    this.dependencies.userCommand.getCommand("cropImage").run();
                },
            },
            resetCrop: {
                load: async ({ editingElement }) => {
                    // todo: This seems quite heavy for a simple reset. Retrieve some
                    // metadata, to load the image crop, to call processImageCrop, just to
                    // reset the crop. We might want to simplify this.
                    const croppedImage = editingElement;

                    const container = document.createElement("div");
                    container.style.display = "none";
                    const originalImage = document.createElement("img");
                    container.append(originalImage);
                    document.body.append(container);

                    const mimetime = getImageMimetype(croppedImage);
                    await loadImage(croppedImage.dataset.originalSrc, originalImage);
                    let aspectRatio = croppedImage.dataset.aspectRatio || "0/0";
                    const cropper = await activateCropper(
                        originalImage,
                        cropperAspectRatios[aspectRatio].value,
                        croppedImage.dataset
                    );
                    cropper.reset();
                    if (aspectRatio !== "0/0") {
                        aspectRatio = "0/0";
                        cropper.setAspectRatio(0);
                    }
                    const newSrc = await processImageCrop(
                        croppedImage,
                        cropper,
                        mimetime,
                        aspectRatio
                    );
                    container.remove();
                    cropper.destroy();
                    return newSrc;
                },
                apply: ({ editingElement, editor, loadResult: newSrc }) => {
                    editingElement.setAttribute("src", newSrc);
                    // todo: Should re-apply a shape if it was applied before.
                    editor.shared.history.addStep();
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
                    this.dependencies.history.addStep();
                },
            },
            glFilter: {
                isApplied: ({ editingElement, param: glFilterName }) => {
                    if (glFilterName) {
                        return editingElement.dataset.glFilter === glFilterName;
                    } else {
                        return !editingElement.dataset.glFilter;
                    }
                },
                load: async ({ editingElement, param: glFilterName }) => {
                    editingElement.dataset.glFilter = glFilterName;
                    const newSrc = await applyModifications(editingElement, {
                        mimetype: getImageMimetype(editingElement),
                    });
                    return newSrc;
                },
                apply: ({ editingElement, editor, loadResult: newSrc }) => {
                    editingElement.setAttribute("src", newSrc);
                    editor.shared.history.addStep();
                },
            },
        };
    }
    async canHaveHoverEffect(img) {
        return (
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

class ImageToolOption extends Component {
    static template = "html_builder.ImageToolOption";
    static components = {
        ...defaultBuilderComponents,
        SpacingOption,
        AddElementOption,
        ImageShapeOption,
    };
    static props = {};
    setup() {
        this.isActiveItem = useIsActiveItem();
    }
}

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
