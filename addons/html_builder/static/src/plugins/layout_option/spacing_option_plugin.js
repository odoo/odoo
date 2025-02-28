import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";

export class SpacingOption extends Component {
    static template = "html_builder.SpacingOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        level: { type: Number, optional: true },
        applyTo: { type: String, optional: true },
    };
    static defaultProps = {
        level: 0,
    };
}
class SpacingOptionPlugin extends Plugin {
    static id = "SpacingOption";
    resources = {
        builder_options: [
            {
                OptionComponent: SpacingOption,
                selector: ".s_masonry_block",
                applyTo: ".o_grid_mode",
            },
        ],
    };
}

registry.category("website-plugins").add(SpacingOptionPlugin.id, SpacingOptionPlugin);
