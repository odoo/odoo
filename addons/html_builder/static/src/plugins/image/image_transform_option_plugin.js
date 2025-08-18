import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ImageTransformation } from "@html_editor/main/media/image_transformation";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Deferred } from "@web/core/utils/concurrency";

export class ImageTransformOptionPlugin extends Plugin {
    static id = "imageTransformOption";
    resources = {
        builder_actions: {
            TransformImageAction,
            ResetTransformImageAction,
        },
    };
}

class TransformImageAction extends BuilderAction {
    static id = "transformImage";
    static dependencies = ["history"];
    isApplied({ editingElement }) {
        return editingElement.matches(`[style*="transform"]`);
    }
    async apply({
        editingElement,
        params: { isImageTransformationOpen, closeImageTransformation },
    }) {
        if (!isImageTransformationOpen()) {
            let changed = false;
            const deferredTillMounted = new Deferred();
            registry.category("main_components").add("ImageTransformation", {
                Component: ImageTransformation,
                props: {
                    image: editingElement,
                    document: this.document,
                    editable: this.editable,
                    destroy: () => closeImageTransformation(),
                    onChange: () => {
                        changed = true;
                    },
                    onApply: () => {
                        if (changed) {
                            changed = false;
                            this.dependencies.history.addStep();
                        }
                    },
                    onComponentMounted: () => {
                        deferredTillMounted.resolve();
                    },
                },
            });
            await deferredTillMounted;
        }
    }
}
class ResetTransformImageAction extends BuilderAction {
    static id = "resetTransformImage";
    static dependencies = ["image"];
    apply({ editingElement, params: { mainParam: closeImageTransformation } }) {
        this.dependencies.image.resetImageTransformation(editingElement);
        closeImageTransformation();
    }
}

registry.category("website-plugins").add(ImageTransformOptionPlugin.id, ImageTransformOptionPlugin);
