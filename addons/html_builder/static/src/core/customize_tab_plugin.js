import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class CustomizeTabPlugin extends Plugin {
    static id = "customizeTab";
    static shared = ["getCustomizeComponent", "openCustomizeComponent", "closeCustomizeComponent"];

    setup() {
        this.customizeComponent = reactive({
            component: null,
            props: {},
            editingEls: null,
        });
        this.closeCustomizeComponent = this.closeCustomizeComponent.bind(this);
    }
    getCustomizeComponent() {
        return this.customizeComponent;
    }
    openCustomizeComponent(component, editingEls, props = {}) {
        this.customizeComponent.component = component;
        this.customizeComponent.editingEls = editingEls;
        this.customizeComponent.props = {
            ...props,
            onClose: this.closeCustomizeComponent,
        };
    }
    closeCustomizeComponent() {
        this.customizeComponent.component = null;
        this.customizeComponent.editingEls = null;
        this.customizeComponent.props = {};
    }
}

registry.category("website-plugins").add(CustomizeTabPlugin.id, CustomizeTabPlugin);
