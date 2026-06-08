import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class AchievementsListOptionPlugin extends Plugin {
    static id = "achievementsListOption";

    resources = {
        is_movable_selectors: { selector: ".s_achievements_list_item", direction: "vertical" },
    };
}

registry
    .category("website-plugins")
    .add(AchievementsListOptionPlugin.id, AchievementsListOptionPlugin);
