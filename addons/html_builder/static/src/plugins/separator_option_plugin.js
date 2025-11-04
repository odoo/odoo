import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BorderConfigurator } from "./border_configurator_option";

class SeparatorOptionPlugin extends Plugin {
    static id = "separatorOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_options: [SeparatorOption],
        dropzone_selector: {
            selector: ".s_hr",
            dropNear: "p, h1, h2, h3, blockquote, .s_hr",
        },
        so_content_addition_selector: [".s_hr"],
        is_movable_selector: { selector: ".s_hr", direction: "vertical" },
    };
}

export class SeparatorOption extends BaseOptionComponent {
    static template = "html_builder.SeparatorOption";
    static selector = ".s_hr";
    static applyTo = "hr";
    static components = { BorderConfigurator };
}
registry.category("builder-plugins").add(SeparatorOptionPlugin.id, SeparatorOptionPlugin);
