import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { SnippetVisibilityOption } from "../options/snippet_visibility_option";
import { withSequence } from "@html_editor/utils/resource";
import { effect } from "@web/core/utils/reactive";
import { DataAttributeAction } from "@html_builder/core/core_builder_action_plugin";

class DataAttributeChangeAction extends DataAttributeAction {
    static id = "dataAttributeChangeAction";
    apply(context) {
        super.apply(context);
        this.config.onChange?.(context);
    }
}

class SnippetVisibilityPlugin extends Plugin {
    static id = "mass_mailing.SnippetVisibility";
    static shared = ["getModel"];

    resources = {
        builder_actions: { DataAttributeChangeAction },
        builder_options: [withSequence(Infinity, SnippetVisibilityOption)],
        system_attributes: "data-filter-domain",
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
        this.config.onChange?.({ isPreviewing: false });
    }
}

registry.category("mass_mailing-plugins").add(SnippetVisibilityPlugin.id, SnippetVisibilityPlugin);
