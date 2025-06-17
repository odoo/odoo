import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ImageTransformation } from "@html_editor/main/media/image_transformation";

export class ImageTransformOptionPlugin extends Plugin {
    static id = "ImageTransformOption";
    static dependencies = ["image", "history"];

    resources = {
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            transformImage: {
                isApplied: ({ editingElement }) => editingElement.matches(`[style*="transform"]`),

                apply: ({ editingElement, params: { closeImageTransformation } }) => {
                    registry.category("main_components").add("ImageTransformation", {
                        Component: ImageTransformation,
                        props: {
                            image: editingElement,
                            document: this.document,
                            editable: this.editable,
                            destroy: () => closeImageTransformation(),
                            onChange: () => this.dependencies.history.addStep(),
                        },
                    });
                },
            },

            resetTransformImage: {
                apply: ({
                    editingElement,
                    params: { isImageTransformationOpen, closeImageTransformation },
                }) => {
                    this.dependencies.image.resetImageTransformation(editingElement);
                    if (isImageTransformationOpen()) {
                        closeImageTransformation();
                    }
                },
            },
        };
    }
}

registry.category("website-plugins").add(ImageTransformOptionPlugin.id, ImageTransformOptionPlugin);
