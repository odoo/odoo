import { ANIMATE, before } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class BadgeOption extends BaseOptionComponent {
    static template = "html_builder.BadgeOption";
    static selector = ".s_badge";
}

class BadgeOptionPlugin extends Plugin {
    static id = "badgeOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_options: [withSequence(before(ANIMATE), BadgeOption)],
        so_content_addition_selector: [".s_badge"],
        unsplittable_node_predicates: (node) => node.classList?.contains("s_badge"),
    };
}
registry.category("builder-plugins").add(BadgeOptionPlugin.id, BadgeOptionPlugin);
