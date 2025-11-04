import { before } from "@html_builder/utils/option_sequence";
import { ANIMATE } from "@website/builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class BadgeOption extends BaseOptionComponent {
    static template = "website.BadgeOption";
    static selector = ".s_badge";
}

class BadgeOptionPlugin extends Plugin {
    static id = "badgeOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_options: [withSequence(before(ANIMATE), BadgeOption)],
        so_content_addition_selector: [".s_badge"],
    };
}
registry.category("website-plugins").add(BadgeOptionPlugin.id, BadgeOptionPlugin);
