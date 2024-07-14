/** @odoo-module */

import { Component } from "@odoo/owl";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

export class LabelProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.Label";
    static components = { Property, SidebarPropertiesToolbox };

    setup() {
        this.editNodeAttributes = useEditNodeAttributes();
    }

    onChangeAttribute(value, name) {
        return this.editNodeAttributes({ [name]: value });
    }
}
