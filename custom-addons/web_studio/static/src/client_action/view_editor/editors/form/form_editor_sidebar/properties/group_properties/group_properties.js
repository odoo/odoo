/** @odoo-module */

import { Component } from "@odoo/owl";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { LimitGroupVisibility } from "@web_studio/client_action/view_editor/interactive_editor/properties/limit_group_visibility/limit_group_visibility";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";
import { ModifiersProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/modifiers/modifiers_properties";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

export class GroupProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.Group";
    static components = {
        ModifiersProperties,
        LimitGroupVisibility,
        Property,
        SidebarPropertiesToolbox,
    };

    setup() {
        this.editNodeAttributes = useEditNodeAttributes();
    }

    onChangeAttribute(value, name) {
        return this.editNodeAttributes({ [name]: value });
    }
}
