import { Plugin } from "@html_editor/plugin";

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
