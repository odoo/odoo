import { useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import { Plugin } from "@html_editor/plugin";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { BackgroundImage } from "./background_image";
import { BackgroundPosition } from "./background_position";
import { BackgroundShape } from "./background_shape";

class BackgroundOptionPlugin extends Plugin {
    static id = "BackgroundOption";
    resources = {
        builder_options: [
            // TODO: add the other options that need BackgroundComponent
            {
                selector: "section",
                OptionComponent: BackgroundComponent,
                props: {
                    withColors: true,
                    withImages: true,
                    // todo: handle with_videos
                    withShapes: true,
                    withGradient: true,
                    withColorCombinations: true,
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

export class BackgroundComponent extends Component {
    static template = "html_builder.BackgroundComponent";
    static components = {
        ...defaultBuilderComponents,
        BackgroundImage,
        BackgroundPosition,
        BackgroundShape,
    };
    static props = {
        withColors: { type: Boolean },
        withImages: { type: Boolean },
        withColorCombinations: { type: Boolean },
        withGradient: { type: Boolean },
        withShapes: { type: Boolean, optional: true },
    };
    static defaultProps = {
        withShapes: false,
    };
    setup() {
        this.isActiveItem = useIsActiveItem();
    }
}
