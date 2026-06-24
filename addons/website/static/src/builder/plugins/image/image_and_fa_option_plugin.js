import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { IMAGE_LINK_ALIGN_CLASSES } from "@html_builder/plugins/image/image_tool_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class WebsiteImageAndFaOptionPlugin extends Plugin {
    static id = "website.ImageAndFaOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            ImageAndFaAlignClassAction,
        },
    };
}

export class ImageAndFaAlignClassAction extends ClassAction {
    static id = "imageAndFaAlignClassAction";
    apply(context) {
        super.apply(context);
        this.syncLinkAlignment(context.editingElement);
    }
    syncLinkAlignment(editingElement) {
        const linkEl = editingElement.parentElement;
        if (
            !linkEl ||
            linkEl.tagName !== "A" ||
            linkEl.firstElementChild !== editingElement ||
            linkEl.childElementCount !== 1 ||
            linkEl.textContent.replace(/\u200B/g, "").trim() // ignore ZWSP
        ) {
            return;
        }
        // Mirror image alignment classes on the wrapping <a> (only when it
        // wraps just this image) so flex layouts stay consistent.
        const alignClasses = IMAGE_LINK_ALIGN_CLASSES.filter((cls) =>
            editingElement.classList.contains(cls)
        );
        for (const className of IMAGE_LINK_ALIGN_CLASSES) {
            linkEl.classList.toggle(className, alignClasses.includes(className));
        }
    }
}

registry
    .category("website-plugins")
    .add(WebsiteImageAndFaOptionPlugin.id, WebsiteImageAndFaOptionPlugin);
