import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Plugin } from "../../plugin";
import { ImageCrop } from "./image_crop";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

/**
 * @typedef { Object } ImageCropShared
 * @property { ImageCropPlugin['openCropImage'] } openCropImage
 */

export class ImageCropPlugin extends Plugin {
    static id = "imageCrop";
    static dependencies = ["selection", "history", "imagePostProcess"];
    static shared = ["openCropImage"];
    resources = {
        user_commands: [
            {
                id: "cropImage",
                run: this.openCropImage.bind(this),
                description: _t("Crop image"),
                icon: "fa-crop",
                isAvailable: isHtmlContentSupported,
            },
        ],
        toolbar_items: [
            {
                id: "image_crop",
                commandId: "cropImage",
                groupId: "image_modifiers",
            },
        ],
    };

    getTargetedImage() {
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        return targetedNodes.find((node) => node.tagName === "IMG");
    }

    async openCropImage(targetedImg, imageCropProps = {}) {
        targetedImg = targetedImg || this.getTargetedImage();
        if (!targetedImg) {
            return;
        }
        return registry.category("main_components").add("ImageCropping", {
            Component: ImageCrop,
            props: {
                media: targetedImg,
                onSave: async (newDataset) => {
                    // todo: should use the mutex if there is one?
                    const updateImageAttributes =
                        await this.dependencies.imagePostProcess.processImage({
                            img: targetedImg,
                            newDataset,
                        });
                    updateImageAttributes();
                    this.dependencies.history.addStep();
                },
                document: this.document,
                ...imageCropProps,
                onClose: () => {
                    registry.category("main_components").remove("ImageCropping");
                    imageCropProps.onClose?.();
                },
            },
        });
    }
}
