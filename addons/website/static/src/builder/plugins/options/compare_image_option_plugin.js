import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ImageToolOption } from "@html_builder/plugins/image/image_tool_option";
import { MediaSizeOption } from "@html_builder/plugins/image/media_size_option";
import { ReplaceMediaOption } from "@html_builder/plugins/image/replace_media_option";

export class CompareImageOptionPlugin extends Plugin {
    static id = "compareImageOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selectors: [".s_compare_image"],
        // Makes the stock image options usable as tags inside this snippet's
        // option template, so each image can be configured in its own section
        // instead of in a separate container.
        builder_components: {
            CompareImageToolOption,
            MediaSizeOption,
            ReplaceMediaOption,
        },
    };
}

// The stock image options minus the shape selector and the size row. Subclassing
// rather than xpath-ing "html_builder.ImageToolOption" in extension mode, which
// would strip those from every image in the builder instead of this snippet's.
export class CompareImageToolOption extends ImageToolOption {
    static template = "website.CompareImageToolOption";
}

registry.category("builder-plugins").add(CompareImageOptionPlugin.id, CompareImageOptionPlugin);
