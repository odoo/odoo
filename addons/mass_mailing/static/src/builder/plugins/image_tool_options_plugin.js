import { ImageToolOption } from "@html_builder/plugins/image/image_tool_option";
import { CropImageAction } from "@html_builder/plugins/image/image_tool_option_plugin";
import { IMAGE_TOOL } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

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
        ],
        builder_options: [
            withSequence(IMAGE_TOOL, {
                template: "mass_mailing.FontAwesomeOption",
                selector: "span.fa, i.fa",
            }),
        ],
    };
}

export class MassMailingImageToolOption extends ImageToolOption {
    static template = "mass_mailing.ImageToolOption";
}

patch(CropImageAction.prototype, {
    setup() {
        super.setup();
        this.withLoadingEffect =
            closestElement(this.editable, ".o_mass_mailing_with_builder") !== null;
    },
});

registry.category("mass_mailing-plugins").add(ImageToolOptionPlugin.id, ImageToolOptionPlugin);
