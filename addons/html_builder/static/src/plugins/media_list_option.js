import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class MediaListOptionPlugin extends Plugin {
    static id = "MediaListOption";
    resources = {
        builder_options: [
            withSequence(5, {
                template: "html_builder.MediaListOption",
                selector: ".s_media_list",
            }),
            withSequence(10, {
                template: "html_builder.MediaListItemOption",
                selector: ".s_media_list_item",
            }),
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            setMediaLayout: {
                isApplied: ({ editingElement, value }) => {
                    const image = editingElement.querySelector(".s_media_list_img_wrapper");
                    return image.classList.contains(`col-lg-${value}`);
                },
                apply: ({ editingElement, value }) => {
                    const image = editingElement.querySelector(".s_media_list_img_wrapper");
                    const content = editingElement.querySelector(".s_media_list_body");
                    image.classList.add(`col-lg-${value}`);
                    content.classList.add(`col-lg-${12 - value}`);
                },
                clean: ({ editingElement, value }) => {
                    const image = editingElement.querySelector(".s_media_list_img_wrapper");
                    const content = editingElement.querySelector(".s_media_list_body");
                    image.classList.remove(`col-lg-${value}`);
                    content.classList.remove(`col-lg-${12 - value}`);
                },
            },
        };
    }
}

registry.category("website-plugins").add(MediaListOptionPlugin.id, MediaListOptionPlugin);
