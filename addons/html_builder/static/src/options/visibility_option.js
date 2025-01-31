import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class VisibilityOptionPlugin extends Plugin {
    static id = "VisibilityOption";
    static dependencies = ["visibilityPlugin"];
    resources = {
        builder_options: [
            {
                template: "html_builder.VisibilityOption",
                selector: "section, .s_hr",
                cleanForSave: this.cleanForSave.bind(this),
            },
        ],
    };

    cleanForSave(editingEl) {
        this.dependencies.visibilityPlugin.cleanForSaveVisibility(editingEl);
    }
}
registry.category("website-plugins").add(VisibilityOptionPlugin.id, VisibilityOptionPlugin);
