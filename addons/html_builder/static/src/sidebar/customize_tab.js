import { Component, useState, useSubEnv } from "@odoo/owl";
import { OptionsContainer } from "./option_container";
import { useVisibilityObserver } from "../core/building_blocks/utils";
import { CustomizeComponent } from "@html_builder/sidebar/customize_component";

export class CustomizeTab extends Component {
    static template = "html_builder.CustomizeTab";
    static components = { CustomizeComponent, OptionsContainer };
    static props = {
        currentOptionsContainers: { type: Array, optional: true },
        snippetModel: { type: Object },
    };
    static defaultProps = {
        currentOptionsContainers: [],
    };

    setup() {
        this.state = useState({
            hasContent: true,
            customizeComponent: null,
        });
        useVisibilityObserver("content", (hasContent) => {
            this.state.hasContent = hasContent;
        });
        useSubEnv({
            openCustomizeComponent: this.openCustomizeComponent.bind(this),
            closeCustomizeComponent: this.closeCustomizeComponent.bind(this),
        });
    }

    openCustomizeComponent(component, editingEls, props = {}) {
        this.state.customizeComponent = {
            comp: component,
            props: props,
            editingEls: editingEls,
        };
    }
    closeCustomizeComponent() {
        this.state.customizeComponent = null;
    }
}
