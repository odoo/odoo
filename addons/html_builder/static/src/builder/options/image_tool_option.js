import { cropperAspectRatios, processImageCrop } from "@html_editor/main/media/image_crop";
import { activateCropper, loadImage } from "@html_editor/utils/image_processing";
import { Component } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { defaultOptionComponents } from "../components/defaultComponents";
import { AddElementOption } from "./add_element_option";
import { SpacingOption } from "./spacing_option";
import { Plugin } from "@html_editor/plugin";

class ImageToolOptionPlugin extends Plugin {
    static id = "ImageToolOption";
    static dependencies = ["history", "userCommand"];
    resources = {
        builder_options: {
            OptionComponent: ImageToolOption,
            selector: "img",
        },
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            cropImage: {
                isActive: ({ editingElement }) => {
                    return editingElement.classList.contains("o_we_image_cropped");
                },
                apply: () => {
                    this.dependencies.userCommand.getCommand("cropImage").run();
                },
            },
            resetCrop: {
                apply: async ({ editingElement }) => {
                    // todo: This seems quite heavy for a simple reset. Retrieve some
                    // metadata, to load the image crop, to call processImageCrop, just to
                    // reset the crop. We might want to simplify this.
                    await loadBundle("html_editor.assets_image_cropper");
                    const croppedImage = editingElement;

                    const container = document.createElement("div");
                    container.style.display = "none";
                    const originalImage = document.createElement("img");
                    container.append(originalImage);
                    document.body.append(container);

                    const mimetime = getImageMimetype(croppedImage);
                    await loadImage(croppedImage.dataset.originalSrc, originalImage);
                    let aspectRatio = croppedImage.dataset.aspectRatio || "0/0";
                    let readyResolve;
                    const readyPromise = new Promise((resolve) => (readyResolve = resolve));
                    const cropper = await activateCropper(
                        originalImage,
                        cropperAspectRatios[aspectRatio].value,
                        croppedImage.dataset,
                        { ready: readyResolve }
                    );
                    await readyPromise;
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
                    croppedImage.setAttribute("src", newSrc);
                    // todo: Should re-apply a shape if it was applied before.
                    this.dependencies.history.addStep();
                },
            },
            transformImage: {
                isActive: ({ editingElement }) => {
                    return editingElement.matches(`[style*="transform"]`);
                },
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
        };
    }
}
registry.category("website-plugins").add(ImageToolOptionPlugin.id, ImageToolOptionPlugin);

class ImageToolOption extends Component {
    static template = "html_builder.ImageToolOption";
    static components = { ...defaultOptionComponents, SpacingOption, AddElementOption };
    static props = {};
}

// const getActions = (plugin) => ();

/**
 * @private
 * @param {HTMLImageElement} img
 * @returns {String} The right mimetype used to apply options on image.
 */
function getImageMimetype(img) {
    if (img.dataset.shape && img.dataset.originalMimetype) {
        return img.dataset.originalMimetype;
    }
    return img.dataset.mimetype;
}
