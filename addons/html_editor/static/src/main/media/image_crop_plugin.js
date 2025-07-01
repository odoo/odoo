import { registry } from "@web/core/registry";
import { Plugin } from "../../plugin";
import { _t } from "@web/core/l10n/translation";
import { ImageCrop } from "./image_crop";
import { loadBundle } from "@web/core/assets";
import { withSequence } from "@html_editor/utils/resource";

export class ImageCropPlugin extends Plugin {
    static id = "imageCrop";
    static dependencies = ["selection", "history"];
    resources = {
        user_commands: [
            {
                id: "cropImage",
                run: this.openCropImage.bind(this),
                title: _t("Crop image"),
                icon: "fa-crop",
            },
        ],
        toolbar_groups: withSequence(27, {
            id: "image_crop",
            namespace: "image",
        }),
        toolbar_items: [
            {
                id: "image_crop",
                commandId: "cropImage",
                groupId: "image_crop",
            },
        ],
    };

    setup() {
        this.imageCropProps = {
            media: undefined,
            mimetype: undefined,
        };
    }

    getSelectedImage() {
        const selectedNodes = this.dependencies.selection.getSelectedNodes();
        return selectedNodes.find((node) => node.tagName === "IMG");
    }

    async openCropImage() {
        const selectedImg = this.getSelectedImage();
        if (!selectedImg) {
            return;
        }

        this.imageCropProps.media = selectedImg;

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
