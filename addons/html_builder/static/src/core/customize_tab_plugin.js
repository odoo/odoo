import { reactive } from "@web/owl2/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } CustomizeTabShared
 * @property { CustomizeTabPlugin['getCustomizeComponent'] } getCustomizeComponent
 * @property { CustomizeTabPlugin['openCustomizeComponent'] } openCustomizeComponent
 * @property { CustomizeTabPlugin['closeCustomizeComponent'] } closeCustomizeComponent
 */

export class CustomizeTabPlugin extends Plugin {
    static id = "customizeTab";
    static shared = ["getCustomizeComponent", "openCustomizeComponent", "closeCustomizeComponent"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        on_redone_handlers: () => this.closeCustomizeComponent(),
        on_undone_handlers: () => this.closeCustomizeComponent(),
        on_current_options_containers_changed_handlers: () => this.closeCustomizeComponent(),
    };

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
        if (this.customizeComponent) {
            this.customizeComponent.component = null;
            this.customizeComponent.editingEls = null;
            this.customizeComponent.props = {};
        }
    }
}

registry.category("builder-plugins").add(CustomizeTabPlugin.id, CustomizeTabPlugin);
