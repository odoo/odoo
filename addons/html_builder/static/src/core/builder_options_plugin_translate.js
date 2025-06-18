import { Plugin } from "@html_editor/plugin";

export class BuilderOptionsPlugin extends Plugin {
    static id = "builderOptions";
    static shared = ["deactivateContainers", "getTarget", "updateContainers"];

    deactivateContainers() {}
    getTarget() {}
    updateContainers() {}
}
