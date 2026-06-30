import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

export class ButtonStrategyPlugin extends Plugin {
    static id = "buttonStrategy";
    static dependencies = [];
    resources = {
        // TODO EGGMAIL rework sequence conflicts: default to sequence 11 to be after image_strategy_plugin
        // element_layout_analysis_processors: withSequence(11, this.analyzeButtonLayout.bind(this)),
    };

    // define style rules specifically for a elements
    // handle conflict with image_strategy_plugin => can not be an imageLink
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ButtonStrategyPlugin.id, ButtonStrategyPlugin);
