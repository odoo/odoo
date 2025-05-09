import { registry } from "@web/core/registry";
import { Plugin } from "../../plugin";
import { _t } from "@web/core/l10n/translation";
import { ImageCrop } from "./image_crop";
import { loadBundle } from "@web/core/assets";

export class ImageCropPlugin extends Plugin {
    static id = "imageCrop";
    static dependencies = ["selection", "history"];
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

    setup() {
        this.imageCropProps = {
            media: undefined,
            mimetype: undefined,
        };
    }

    /**
     * @deprecated
     */
    getSelectedImage() {
        return this.getTargetedImage();
    }

    getTargetedImage() {
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        return targetedNodes.find((node) => node.tagName === "IMG");
    }

    async openCropImage() {
        const targetedImg = this.getTargetedImage();
        if (!targetedImg) {
            return;
        }

        this.imageCropProps.media = targetedImg;

        const onClose = () => {
            registry.category("main_components").remove("ImageCropping");
        };

        const onSave = () => {
            this.dependencies.history.addStep();
        };

        await loadBundle("html_editor.assets_image_cropper");

        registry.category("main_components").add("ImageCropping", {
            Component: ImageCrop,
            props: { ...this.imageCropProps, onClose, onSave, document: this.document },
        });
    }
}
