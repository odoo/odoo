import { Plugin } from "@html_editor/plugin";
import { MassMailingColorPicker } from "../color_picker";
import { registry } from "@web/core/registry";

class MassMailingColorPickerPlugin extends Plugin {
    static id = "mass_mailing.ColorPickerPlugin";
    resources = {
        builder_components: {
            MassMailingColorPicker,
        },
    };
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingColorPickerPlugin.id, MassMailingColorPickerPlugin);
