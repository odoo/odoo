import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { SnippetVisibilityOption } from "../options/snippet_visibility_option";
import { withSequence } from "@html_editor/utils/resource";
import { effect } from "@web/core/utils/reactive";

class SnippetVisibilityPlugin extends Plugin {
    static id = "mass_mailing.SnippetVisibility";
    static shared = ["getModel"];

    resources = {
        builder_options: [withSequence(Infinity, SnippetVisibilityOption)],
    };
    setup() {
        this.mailingModelId = this.config.record.data.mailing_model_id.id;
        effect(
            (record) => {
                if (this.isDestroyed) {
                    return;
                }
                if (record.data.mailing_model_id.id !== this.mailingModelId) {
                    this.mailingModelId = record.data.mailing_model_id.id;
                    this.resetFilterDomains();
                }
            },
            [this.config.record]
        );
    }

    getModel() {
        return this.config.record.data.mailing_model_real;
    }

    resetFilterDomains() {
        const filteredElements = this.editable.querySelectorAll("[data-filter-domain]");
        filteredElements.forEach((el) => el.removeAttribute("data-filter-domain"));
        this.dispatchTo("trigger_dom_updated");
    }
}

registry.category("mass_mailing-plugins").add(SnippetVisibilityPlugin.id, SnippetVisibilityPlugin);
