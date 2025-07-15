import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class EditInteractionPlugin extends Plugin {
    static id = "edit_interaction";

    static shared = ["restartInteractions"];

    resources = {
        normalize_handlers: this.refreshInteractions.bind(this),
        content_manually_updated_handlers: this.refreshInteractions.bind(this),
        before_save_handlers: () => this.stopInteractions(),
        on_will_clone_handlers: ({ originalEl }) => {
            this.stopInteractions(originalEl);
        },
        on_cloned_handlers: ({ originalEl }) => {
            this.restartInteractions(originalEl);
            // The clonedEl is implicitly started because it is a newly
            // inserted content.
        },
        // Resource definitions:
        skip_refresh_on_snippet_save: [
            // List of snippet selectors for which interaction refresh should be
            // disabled on save. This is mainly because the interaction clears
            // the content before it can be cloned and saved.
        ],
        on_will_save_snippet_handlers: ({ snippetEl }) => {
            if (!snippetEl.matches(this.getResource("skip_refresh_on_snippet_save").join(", "))) {
                this.stopInteractions(snippetEl);
            }
        },
        on_saved_snippet_handlers: ({ snippetEl }) => {
            if (!snippetEl.matches(this.getResource("skip_refresh_on_snippet_save").join(", "))) {
                this.restartInteractions(snippetEl);
            }
        },
    };

    setup() {
        this.websiteEditService = undefined;
        this.areInteractionsStartedInEditMode = false;

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
        this.websiteEditService.update(element, "edit");
        this.areInteractionsStartedInEditMode = true;
    }

    refreshInteractions(element) {
        if (this.areInteractionsStartedInEditMode) {
            this.websiteEditService.refresh(element);
        } else {
            this.restartInteractions(element);
        }
    }

    stopInteractions(element) {
        if (!this.websiteEditService) {
            throw new Error("website edit service not loaded");
        }
        this.websiteEditService.stop(element);
    }
}

registry.category("website-plugins").add(EditInteractionPlugin.id, EditInteractionPlugin);
