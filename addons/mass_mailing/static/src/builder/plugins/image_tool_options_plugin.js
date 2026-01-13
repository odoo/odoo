import { CropImageAction } from "@html_builder/plugins/image/image_tool_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { MassMailingImageToolOption } from "@mass_mailing/builder/options/image_tool_option";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

class ImageToolOptionPlugin extends Plugin {
    static id = "mass_mailing.ImageToolOption";
    resources = {
        patch_builder_options: [
            {
                target_name: "imageToolOption",
                target_element: "OptionComponent",
                method: "replace",
                value: MassMailingImageToolOption,
            },
        ],
    };
}

patch(CropImageAction.prototype, {
    setup() {
        super.setup();
        this.withLoadingEffect =
            closestElement(this.editable, ".o_mass_mailing_with_builder") !== null;
    },
});

registry.category("mass_mailing-plugins").add(ImageToolOptionPlugin.id, ImageToolOptionPlugin);
