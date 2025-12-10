import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class WebsiteBackgroundShapeOptionPlugin extends Plugin {
    static id = "websiteBackgroundShapeOption";
    static dependencies = ["backgroundShapeOption"];
    resources = {
        on_visibility_toggled_handlers: this.visibilityToggledHandler.bind(this),
    };
    visibilityToggledHandler(editingElement) {
        this.dependencies.backgroundShapeOption.handleBgColorUpdated(editingElement);
    }
}

registry
    .category("website-plugins")
    .add(WebsiteBackgroundShapeOptionPlugin.id, WebsiteBackgroundShapeOptionPlugin);
