import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BorderConfigurator } from "./border_configurator_option";

export class SeparatorOptionPlugin extends Plugin {
    static id = "separatorOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        dropzone_selector: {
            selector: ".s_hr",
            dropNear: "p, h1, h2, h3, blockquote, .s_hr",
        },
        so_content_addition_selector: [".s_hr"],
        is_movable_selector: { selector: ".s_hr", direction: "vertical" },
    };
}
registry.category("builder-plugins").add(SeparatorOptionPlugin.id, SeparatorOptionPlugin);

export class SeparatorOption extends BaseOptionComponent {
    static id = "separator_option";
    static template = "html_builder.SeparatorOption";
    static components = { BorderConfigurator };
}
registry.category("builder-options").add(SeparatorOption.id, SeparatorOption);
