import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { Plugin } from "@html_editor/plugin";
import { BuilderOptionsPlugin } from "./builder_options_plugin";

/** @typedef {import("./builder_options_plugin").BuilderOptionContainer[]} translate_options */

export class BuilderOptionsTranslationPlugin extends Plugin {
    static id = "builderOptions";
    static shared = [
        "deactivateContainers",
        "getTarget",
        "updateContainers",
        "setNextTarget",
        "getBuilderOptionContext",
        "getRemoveDisabledReason",
        "getCloneDisabledReason",
    ];
    static dependencies = ["history"];

    setup() {
        this.builderOptions = this.getResource("translate_options");
        this.builderOptionsContext = new Map();
        this.builderOptionsDependencies = new Map();
        const options = this.builderOptions.concat([OptionsContainer]);
        for (const Option of options) {
            this.getBuilderDependencies(Option);
            this.getBuilderOptionContext(Option);
        }
    }
    deactivateContainers() {}
    getTarget() {}
    getRemoveDisabledReason() {}
    getCloneDisabledReason() {}
    updateContainers() {}
    setNextTarget(targetEl) {
        // Store the next target to activate in the current step.
        this.dependencies.history.setStepExtra("nextTarget", targetEl);
    }
}

BuilderOptionsTranslationPlugin.prototype.getBuilderDependencies =
    BuilderOptionsPlugin.prototype.getBuilderDependencies;
BuilderOptionsTranslationPlugin.prototype.getBuilderOptionContext =
    BuilderOptionsPlugin.prototype.getBuilderOptionContext;
