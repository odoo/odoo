import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { SnippetVisibilityOption } from "../options/snippet_visibility_option";
import { withSequence } from "@html_editor/utils/resource";
import { effect } from "@web/core/utils/reactive";

class SnippetVisibilityPlugin extends Plugin {
    static id = "mass_mailing.SnippetVisibility";

    resources = {
        builder_options: [
            withSequence(Infinity, {
                OptionComponent: SnippetVisibilityOption,
                selector: "section",
                props: {
                    getModel: () => this.config.record.data.mailing_model_real,
                },
            }),
        ],
    };
    setup() {
        super.setup();
        this.mailingModelId = this.config.record.data.mailing_model_id.id;
        effect(
            (record) => {
                if (this.isDestroyed) {
                    return;
                }
                if (record.data.mailing_model_id.id !== this.mailingModelId) {
                    this.mailingModelId = record.data.mailing_model_id.id;
                    this.updateFilterDomains();
                }
            },
            [this.config.record]
        );
    }

    updateFilterDomains() {
        const filteredElements = this.editable.querySelectorAll("[data-filter-domain]");
        filteredElements.forEach((el) => el.removeAttribute("data-filter-domain"));
        this.dispatchTo("trigger_dom_updated");
    }
}

registry.category("mass_mailing-plugins").add(SnippetVisibilityPlugin.id, SnippetVisibilityPlugin);
