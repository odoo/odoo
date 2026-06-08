import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { renderToElement } from "@web/core/utils/render";

export class MediaListOptionPlugin extends Plugin {
    static id = "mediaListOption";
    mediaListItemOptionSelector = ".s_media_list_item";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetMediaLayoutAction,
            AddMediaImageAction,
        },
        mark_color_level_selector_params: [
            { selector: ".s_media_list_item", applyTo: ":scope > .row" },
        ],
    };
}

export class SetMediaLayoutAction extends BuilderAction {
    static id = "setMediaLayout";
    isApplied({ editingElement, value }) {
        const image = editingElement.querySelector(".s_media_list_img_wrapper");
        return image?.classList.contains(`col-lg-${value}`) || false;
    }
    apply({ editingElement, value }) {
        const image = editingElement.querySelector(".s_media_list_img_wrapper");
        const content = editingElement.querySelector(".s_media_list_body");
        image.classList.add(`col-lg-${value}`);
        content.classList.add(`col-lg-${12 - value}`);
    }
    clean({ editingElement, value }) {
        const image = editingElement.querySelector(".s_media_list_img_wrapper");
        const content = editingElement.querySelector(".s_media_list_body");
        image.classList.remove(`col-lg-${value}`);
        content.classList.remove(`col-lg-${12 - value}`);
    }
}

export class AddMediaImageAction extends BuilderAction {
    static id = "addMediaImage";
    apply({ editingElement }) {
        const imageEl = renderToElement("website.s_media_list.imageWrapper");
        const contentEl = editingElement.querySelector(".s_media_list_body");
        const contentCol = [...contentEl.classList].find((className) =>
            className.startsWith("col-lg-")
        );
        contentEl.classList.remove(contentCol);
        contentEl.classList.add("col-lg-8");
        editingElement.querySelector(":scope > .row").prepend(imageEl);
    }
}

registry.category("website-plugins").add(MediaListOptionPlugin.id, MediaListOptionPlugin);
