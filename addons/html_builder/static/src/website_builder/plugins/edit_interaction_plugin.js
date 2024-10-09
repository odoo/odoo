import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class EditInteractionPlugin extends Plugin {
    static id = "edit_interaction";

    resources = {
        update_interactions: this.startInteractions.bind(this),
        on_remove_handlers: this.stopInteractions.bind(this),
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
        const targetEl = this.document.querySelector("#wrapwrap");
        this.startInteractions(targetEl);
    }

    startInteractions(element) {
        if (!this.websiteEditService) {
            throw new Error("website edit service not loaded");
        }
        this.websiteEditService.update(element, true);
    }

    stopInteractions(element) {
        if (!this.websiteEditService) {
            throw new Error("website edit service not loaded");
        }
        this.websiteEditService.stop(element);
    }
}

registry.category("website-plugins").add(EditInteractionPlugin.id, EditInteractionPlugin);
