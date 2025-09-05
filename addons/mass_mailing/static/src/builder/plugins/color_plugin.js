import { ColorPlugin } from "@html_builder/core/color_plugin";
import { registry } from "@web/core/registry";

export class MassMailingColorPlugin extends ColorPlugin {
    getPropsForColorSelector(type) {
        const props = { ...super.getPropsForColorSelector(type) };
        props.enabledTabs = ["solid", "custom"];
        return props;
    }
}

registry.category("mass_mailing-plugins").add(MassMailingColorPlugin.id, MassMailingColorPlugin);
