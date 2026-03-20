import { ImagePlugin as EditorImagePlugin } from "@html_editor/main/media/image_plugin";
import { DISABLED_NAMESPACE } from "@html_editor/main/toolbar/toolbar_plugin";

export class ImagePlugin extends EditorImagePlugin {
    static shared = ["resetImageTransformation"];
    toolbarNamespace = DISABLED_NAMESPACE;
    resources = {
        ...this.resources,
        on_will_save_media_dialog_handlers: async (elements) => {
            for (const element of elements) {
                if (element && element.tagName === "IMG") {
                    this.resetImageTransformation(element, { addStep: false });
                }
            }
        },
    };

    resetImageTransformation(image, { addStep = true } = {}) {
        [
            "transform",
            "transform-box",
            "transform-origin",
            "transform-style",
            "width",
            "height",
        ].forEach((prop) => image.style.removeProperty(prop));
        if (addStep) {
            this.dependencies.history.addStep();
        }
    }
}
