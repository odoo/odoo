import { before } from "@html_builder/utils/option_sequence";
import { ANIMATE } from "@website/builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class BadgeOptionPlugin extends Plugin {
    static id = "badgeOption";
    resources = {
        builder_options: [
            withSequence(before(ANIMATE), {
                template: "website.BadgeOption",
                selector: ".s_badge",
            }),
        ],
        so_content_addition_selector: [".s_badge"],
    };
}
registry.category("website-plugins").add(BadgeOptionPlugin.id, BadgeOptionPlugin);
