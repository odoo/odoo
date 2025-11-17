import { Plugin } from "@html_editor/plugin";

/** @typedef {import("./builder_options_plugin").BuilderOptionContainer[]} translate_options */

export class BuilderOptionsTranslationPlugin extends Plugin {
    static id = "builderOptions";
    static shared = ["deactivateContainers", "getTarget", "updateContainers", "setNextTarget"];
    static dependencies = ["history"];

    deactivateContainers() {}
    getTarget() {}
    updateContainers() {}
    setNextTarget(targetEl) {
        // Store the next target to activate in the current step.
        this.dependencies.history.setStepExtra("nextTarget", targetEl);
    }
}
