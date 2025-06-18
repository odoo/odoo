import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BuilderOptionsPlugin extends Plugin {
    static id = "builderOptions";
    static shared = ["deactivateContainers", "getTarget", "updateContainers"];

    deactivateContainers() {}
    getTarget() {}
    updateContainers() {}
}

registry.category("translation-plugins").add(BuilderOptionsPlugin.id, BuilderOptionsPlugin);
