import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { ImageToolOption } from "@html_builder/plugins/image/image_tool_option";
import { ReplaceMediaOption } from "@html_builder/plugins/image/replace_media_option";

export class CompareImageOptionPlugin extends Plugin {
    static id = "compareImageOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selectors: [".s_compare_image"],
        // Clicking an image targets the image itself, and only the innermost
        // container with options gets unfolded, so the snippet's own options
        // would stay collapsed. No-op once the images are not selectable.
        auto_unfold_container_providers: {
            selector: ".s_compare_image img",
            target: ".s_compare_image",
        },
        // Makes the stock image options usable as tags inside this snippet's
        // option template, so each image can be configured in its own section
        // instead of in a separate container.
        builder_components: {
            CompareImageToolOption,
            ReplaceMediaOption,
        },
        builder_actions: {
            CompareImageAction,
        },
    };
}

// The stock image options minus the shape selector. Subclassing rather than
// xpath-ing "html_builder.ImageToolOption" in extension mode, which would strip
// shapes from every image in the builder instead of just this snippet's.
export class CompareImageToolOption extends ImageToolOption {
    static template = "website.CompareImageToolOption";
}

export class CompareImageAction extends BuilderAction {
    static id = "compareImage";
}

registry.category("builder-plugins").add(CompareImageOptionPlugin.id, CompareImageOptionPlugin);
