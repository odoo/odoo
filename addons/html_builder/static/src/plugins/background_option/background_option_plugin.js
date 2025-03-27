import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BackgroundOptionPlugin extends Plugin {
    static id = "backgroundOption";
    resources = {
        normalize_handlers: this.normalize.bind(this),
        system_classes: ["o_colored_level"],
    };
    normalize(root) {
        const markColorLevelSelectorParams = this.getResource("mark_color_level_selector_params");
        for (const markColorLevelSelectorParam of markColorLevelSelectorParams) {
            applyFunDependOnSelectorAndExclude(
                this.markColorLevel,
                root,
                markColorLevelSelectorParam
            );
        }
    }
    markColorLevel(editingEl) {
        editingEl.classList.add("o_colored_level");
    }
}
registry.category("website-plugins").add(BackgroundOptionPlugin.id, BackgroundOptionPlugin);
