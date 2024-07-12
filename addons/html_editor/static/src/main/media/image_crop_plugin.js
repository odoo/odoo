import { registry } from "@web/core/registry";
import { Plugin } from "../../plugin";
import { _t } from "@web/core/l10n/translation";
import { ImageCrop } from "./image_crop";
import { loadBundle } from "@web/core/assets";

export class ImageCropPlugin extends Plugin {
    static name = "image_crop";
    static dependencies = ["image", "selection"];
    /** @type { (p: ImageCropPlugin) => Record<string, any> } */
    static resources(p) {
        return {
            toolbarGroup: [
                {
                    id: "image_crop",
                    namespace: "image",
                    sequence: 27,
                    buttons: [
                        {
                            id: "image_crop",
                            name: _t("Crop image"),
                            icon: "fa-crop",
                            action(dispatch) {
                                dispatch("CROP_IMAGE");
                            },
                        },
                    ],
                },
            ],
        };
    }

    setup() {
        this.imageCropProps = {
            media: undefined,
            mimetype: undefined,
        };
    }

    handleCommand(command, payload) {
        switch (command) {
            case "CROP_IMAGE": {
                const selectedImg = this.getSelectedImage();
                if (!selectedImg) {
                    return;
                }
                this.imageCropProps.media = selectedImg;
                this.openCropImage();
                break;
            }
        }
    }

    getSelectedImage() {
        const selectedNodes = this.shared.getSelectedNodes();
        return selectedNodes.find((node) => node.tagName === "IMG");
    }

    async openCropImage() {
        const onClose = () => {
            registry.category("main_components").remove("ImageCropping");
        };

        const onSave = () => {
            this.dispatch("ADD_STEP");
        };

        await loadBundle("html_editor.assets_image_cropper");

        registry.category("main_components").add("ImageCropping", {
            Component: ImageCrop,
            props: { ...this.imageCropProps, onClose, onSave, document: this.document },
        });
    }
}
registry.category("phoenix_plugins").add(ImageCropPlugin.name, ImageCropPlugin);
