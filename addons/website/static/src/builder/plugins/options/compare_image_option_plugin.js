import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { ImageToolOption } from "@html_builder/plugins/image/image_tool_option";
import { MediaSizeOption } from "@html_builder/plugins/image/media_size_option";
import { ReplaceMediaOption } from "@html_builder/plugins/image/replace_media_option";

export class CompareImageOptionPlugin extends Plugin {
    static id = "compareImageOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selectors: [".s_compare_image"],
        // GridImageOption is declared without `exclude`, which makes the
        // builder skip the images' "o_snippet_not_selectable": clicking one
        // gives it an empty container, unfolded instead of this snippet's.
        auto_unfold_container_providers: {
            selector: ".s_compare_image img",
            target: ".s_compare_image",
        },
    };
}

export class CompareImageToolOption extends ImageToolOption {
    static template = "website.CompareImageToolOption";
}

// The image options are given as this option's own components rather than
// through the "builder_components" resource: that one is shared by every
// option, translation ones included, which would then require the image
// plugins that the translation mode does not load.
export class CompareImageOption extends BaseOptionComponent {
    static id = "compare_image_option";
    static template = "website.CompareImage";
    static components = {
        CompareImageToolOption,
        MediaSizeOption,
        ReplaceMediaOption,
    };
}

registry.category("builder-plugins").add(CompareImageOptionPlugin.id, CompareImageOptionPlugin);
registry.category("website-options").add(CompareImageOption.id, CompareImageOption);
