import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BackgroundOption } from "./background_option";

class BackgroundOptionPlugin extends Plugin {
    static id = "backgroundOption";
    resources = {
        builder_options: [
            // TODO: add the other options that need BackgroundComponent
            {
                selector: "section",
                OptionComponent: BackgroundOption,
                props: {
                    withColors: true,
                    withImages: true,
                    // todo: handle with_videos
                    withShapes: true,
                    withGradient: true,
                    withColorCombinations: true,
                },
            },
            // Background-color only
            {
                selector: ".s_chart",
                OptionComponent: BackgroundOption,
                props: {
                    withColors: true,
                    withImages: false,
                    withGradient: true,
                    withColorCombinations: false,
                },
            },
        ],
        normalize_handlers: this.normalize.bind(this),
        system_classes: ["o_colored_level"],
    };
    setup() {
        this.coloredLevelBackgroundParams = [];
        for (const builderOption of this.resources.builder_options) {
            if (builderOption.props.withColors && builderOption.props.withColorCombinations) {
                this.coloredLevelBackgroundParams.push({
                    selector: builderOption.selector,
                    exclude: builderOption.exclude || "",
                });
            }
        }
    }
    normalize(root) {
        for (const coloredLevelBackgroundParam of this.coloredLevelBackgroundParams) {
            applyFunDependOnSelectorAndExclude(
                this.markColorLevel,
                root,
                coloredLevelBackgroundParam.selector,
                coloredLevelBackgroundParam.exclude
            );
        }
    }
    markColorLevel(editingEl) {
        editingEl.classList.add("o_colored_level");
    }
}
registry.category("website-plugins").add(BackgroundOptionPlugin.id, BackgroundOptionPlugin);
