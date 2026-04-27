/** @odoo-module */

import { Component } from "@odoo/owl";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { LimitGroupVisibility } from "@web_studio/client_action/view_editor/interactive_editor/properties/limit_group_visibility/limit_group_visibility";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";
import { ModifiersProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/modifiers/modifiers_properties";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

class PageNodeToolbox extends SidebarPropertiesToolbox {
    removeNodeFromArch() {
        const node = this.node;
        let xpathToRemove = node.xpath;
        if (node.arch.parentElement.children.length <= 1) {
            // retarget to the parent notebook
            xpathToRemove = node.xpath.split("/").slice(0, -1).join("/");
        }
        return super.removeNodeFromArch(xpathToRemove);
    }
}

export class PageProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.Page";
    static components = {
        Property,
        LimitGroupVisibility,
        PageNodeToolbox,
        ModifiersProperties,
    };

    setup() {
        this.editNodeAttributes = useEditNodeAttributes();
    }

    onChangeAttribute(value, name) {
        return this.editNodeAttributes({ [name]: value });
    }

    static props = {
        node: { type: Object },
    }
}
