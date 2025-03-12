import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class EditInteractionPlugin extends Plugin {
    static id = "edit_interaction";

    resources = {
        normalize_handlers: this.restartInteractions.bind(this),
        option_visibility_updated: this.restartInteractions.bind(this),
        content_manually_updated_handlers: this.restartInteractions.bind(this),
    };

    setup() {
        this.websiteEditService = undefined;

        window.parent.document.addEventListener(
            "transfer_website_edit_service",
            this.updateEditInteraction.bind(this),
            { once: true }
        );
        window.parent.document.dispatchEvent(new CustomEvent("edit_interaction_plugin_loaded"));
    }

    updateEditInteraction({ detail: { websiteEditService } }) {
        this.websiteEditService = websiteEditService;
    }

    restartInteractions(element) {
        if (!this.websiteEditService) {
            throw new Error("website edit service not loaded");
        }
        this.websiteEditService.update(element, true);
    }
}

registry.category("website-plugins").add(EditInteractionPlugin.id, EditInteractionPlugin);
