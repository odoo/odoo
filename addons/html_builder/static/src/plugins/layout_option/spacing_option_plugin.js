import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useBuilderComponents } from "@html_builder/core/utils";

export class SpacingOption extends Component {
    static template = "html_builder.SpacingOption";
    static props = {
        level: { type: Number, optional: true },
        applyTo: { type: String, optional: true },
    };
    static defaultProps = {
        level: 0,
    };
    setup() {
        useBuilderComponents();
    }
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
