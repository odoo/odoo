import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import { getSelectorParams } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BackgroundOption } from "./background_option";

class BackgroundOptionPlugin extends Plugin {
    static id = "backgroundOption";
    resources = {
        normalize_handlers: this.normalize.bind(this),
        system_classes: ["o_colored_level"],
    };
    setup() {
        this.coloredLevelBackgroundParams = getSelectorParams(
            this.getResource("builder_options"),
            BackgroundOption
        );
    }
    normalize(root) {
        for (const coloredLevelBackgroundParam of this.coloredLevelBackgroundParams) {
            applyFunDependOnSelectorAndExclude(
                this.markColorLevel,
                root,
                coloredLevelBackgroundParam
            );
        }
    }
    markColorLevel(editingEl) {
        editingEl.classList.add("o_colored_level");
    }
}
registry.category("website-plugins").add(BackgroundOptionPlugin.id, BackgroundOptionPlugin);
