import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef {{
 *     selector: CSSSelector;
 *     exclude?: CSSSelector;
 *     applyTo?: CSSSelector;
 * }[]} mark_color_level_selector_params
 */

class BackgroundOptionPlugin extends Plugin {
    static id = "backgroundOption";
    /** @type {import("plugins").BuilderResources} */
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
registry.category("builder-plugins").add(BackgroundOptionPlugin.id, BackgroundOptionPlugin);
