import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class EditInteractionPlugin extends Plugin {
    static id = "edit_interaction";

    resources = {
        normalize_handlers: this.restartInteractions.bind(this),
        content_manually_updated_handlers: this.restartInteractions.bind(this),
        before_save_handlers: () => this.stopInteractions(),
        on_will_clone_handlers: ({ originalEl }) => {
            this.stopInteractions(originalEl);
        },
        on_cloned_handlers: ({ originalEl }) => {
            this.restartInteractions(originalEl);
            // The clonedEl is implicitly started because it is a newly
            // inserted content.
        },
    };

    setup() {
        this.websiteEditService = undefined;

        window.parent.document.addEventListener(
            "transfer_website_edit_service",
            this.updateEditInteraction.bind(this),
            { once: true }
        );
        const event = new CustomEvent("edit_interaction_plugin_loaded");
        event.shared = this.config.getShared();
        window.parent.document.dispatchEvent(event);
    }
    destroy() {
        this.websiteEditService?.uninstallPatches?.();
        this.stopInteractions();
    }

    updateEditInteraction({ detail: { websiteEditService } }) {
        this.websiteEditService = websiteEditService;
        this.websiteEditService.installPatches();
    }

    restartInteractions(element) {
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
