import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { DataAttributeAction } from "@html_builder/core/core_builder_action_plugin";
import { effect } from "@odoo/owl";

class DataAttributeChangeAction extends DataAttributeAction {
    static id = "dataAttributeChangeAction";
    apply(context) {
        super.apply(context);
        this.config.onChange?.(context);
    }
    isApplied({ editingElement, params: { mainParam: attributeName } = {}, value }) {
        if (value) {
            return Boolean(editingElement.dataset[attributeName]) === Boolean(value);
        } else {
            return super.isApplied(...arguments);
        }
    }
}

export class SnippetVisibilityPlugin extends Plugin {
    static id = "mass_mailing.SnippetVisibility";
    static shared = ["getModel"];

    resources = {
        builder_actions: { DataAttributeChangeAction },
        system_attributes: "data-filter-domain",
    };
    setup() {
        this.mailingModelId = this.config.record.data.mailing_model_id.id;
        const disposeEffect = effect(() => {
            if (this.isDestroyed) {
                return;
            }
            if (this.config.record.data.mailing_model_id.id !== this.mailingModelId) {
                this.mailingModelId = this.config.record.data.mailing_model_id.id;
                this.resetFilterDomains();
            }
        });
        this._cleanups.push(disposeEffect);
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
