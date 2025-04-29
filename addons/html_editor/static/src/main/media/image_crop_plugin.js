import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Plugin } from "../../plugin";
import { ImageCrop } from "./image_crop";

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

    getSelectedImage() {
        const selectedNodes = this.dependencies.selection.getSelectedNodes();
        return selectedNodes.find((node) => node.tagName === "IMG");
    }

    async openCropImage(selectedImg, imageCropProps) {
        selectedImg = selectedImg || this.getSelectedImage();
        if (!selectedImg) {
            return;
        }
        return registry.category("main_components").add("ImageCropping", {
            Component: ImageCrop,
            props: {
                media: selectedImg,
                onSave: async (newDataset) => {
                    // todo: should use the mutex if there is one?
                    const updateImageAttributes =
                        await this.dependencies.imagePostProcess.processImage(
                            selectedImg,
                            newDataset
                        );
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
