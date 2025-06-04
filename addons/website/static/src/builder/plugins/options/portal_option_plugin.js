import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { StyleAction } from "@html_builder/core/core_builder_action_plugin";

class PortalCardOptionPlugin extends Plugin {
    static id = "PortalOption";
    static dependencies = ["customizeWebsite"];

    resources = {
        builder_options: [
            withSequence(1, {
                template: "website.PortalOption",
                selector: ".o_portal",
            }),
        ],
    builder_actions: { 
        StyleActionPortalAction 
        },
    };
} 

class StyleActionPortalAction extends StyleAction {
    static id = "styleActionPortal";
    static dependencies = ["customizeWebsite", "color"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }

    async apply({ params, value }) {
        const styleName = params.mainParam;

        if (styleName === "border-color") {
            return this.dependencies.customizeWebsite.customizeWebsiteColors({
                "menu-border-card-color": value,
            });
        }

        const variableMap = {
            "border-style": "menu-border-card-style",
            "border-radius": "menu-border-card-radius",
            "border-width": "menu-border-card-width",
        };

        if (styleName in variableMap) {
            return this.dependencies.customizeWebsite.customizeWebsiteVariables({
                [variableMap[styleName]]: value,
            });
        }
    }   
}
registry.category("website-plugins").add(PortalCardOptionPlugin.id, PortalCardOptionPlugin);
