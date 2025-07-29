import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BuilderContentEditablePlugin extends Plugin {
    static id = "builderContentEditablePlugin";
    resources = {
        force_not_editable_selector: [
            "section:has(> .o_container_small, > .container, > .container-fluid)",
        ],
        force_editable_selector: [
            "section > .o_container_small",
            "section > .container",
            "section > .container-fluid",
        ],
    };
}
registry
    .category("website-plugins")
    .add(BuilderContentEditablePlugin.id, BuilderContentEditablePlugin);
