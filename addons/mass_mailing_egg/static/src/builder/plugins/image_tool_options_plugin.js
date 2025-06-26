import { ImageToolOption } from "@html_builder/plugins/image/image_tool_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ImageToolOptionPlugin extends Plugin {
    static id = "mass_mailing.ImageToolOption";
    resources = {
        patch_builder_options: [
            {
                target_name: "imageAndFaOption",
                target_element: "template",
                method: "replace",
                value: "mass_mailing.ImageAndFaOption",
            },
            {
                target_name: "imageAndFaOption",
                target_element: "exclude",
                method: "remove",
            },
            {
                target_name: "imageToolOption",
                target_element: "OptionComponent",
                method: "replace",
                value: MassMailingImageToolOption,
            },
        ]
    }
}

class MassMailingImageToolOption extends ImageToolOption {
    static template = "mass_mailing.ImageToolOption";
}

registry.category("builder-plugins").add(ImageToolOptionPlugin.id, ImageToolOptionPlugin);
