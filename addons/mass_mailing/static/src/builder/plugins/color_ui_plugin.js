import { ColorUIPlugin } from "@html_builder/core/color_ui_plugin";
import { registry } from "@web/core/registry";

export class MassMailingColorUIPlugin extends ColorUIPlugin {
    getPropsForColorSelector(type) {
        const props = { ...super.getPropsForColorSelector(type) };
        props.enabledTabs = ["solid", "custom"];
        return props;
    }
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingColorUIPlugin.id, MassMailingColorUIPlugin);
