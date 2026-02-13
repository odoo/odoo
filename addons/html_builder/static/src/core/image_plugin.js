import { ImagePlugin as EditorImagePlugin } from "@html_editor/main/media/image_plugin";
import { DISABLED_NAMESPACE } from "@html_editor/main/toolbar/toolbar_plugin";

export class ImagePlugin extends EditorImagePlugin {
    toolbarNamespace = DISABLED_NAMESPACE;
    static dependencies = [...super.dependencies, "imageSave"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        before_save_handlers: this.dependencies.imageSave.savePendingImages,
    };
}
