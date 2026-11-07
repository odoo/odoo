import { Plugin } from "@html_editor/plugin";
import { handleImagesIfDataset } from "@html_builder/utils/image";
import { registry } from "@web/core/registry";

export class JsonldPlugin extends Plugin {
    static id = "jsonld";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        // the media dialog builds a new image: keep the JSON-LD property of the replaced one
        on_will_save_media_dialog_handlers: (elements, { node }) =>
            handleImagesIfDataset(elements, node, "jsonldProp", (imageEl, oldImageEl) => {
                imageEl.dataset.jsonldProp = oldImageEl.dataset.jsonldProp;
            }),
    };
}

registry.category("website-plugins").add(JsonldPlugin.id, JsonldPlugin);
