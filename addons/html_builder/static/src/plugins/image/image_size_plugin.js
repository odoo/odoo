import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ImageSize } from "./image_size";

class ImageSizePlugin extends Plugin {
    static id = "imageSize";
    static dependencies = ["imagePostProcess"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        elements_to_options_title_components: {
            Component: ImageSize,
            selector: "img",
        },
    };
}
registry.category("builder-plugins").add(ImageSizePlugin.id, ImageSizePlugin);
