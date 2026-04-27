/** @odoo-module */

import { Component } from "@odoo/owl";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { ModifiersProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/modifiers/modifiers_properties";
import { ViewStructureProperties } from "@web_studio/client_action/view_editor/interactive_editor/properties/view_structure_properties/view_structure_properties";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

export class GroupProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.Group";
    static components = {
        ModifiersProperties,
        Property,
        ViewStructureProperties,
    };
    static props = ["node"];

    setup() {
        this.editNodeAttributes = useEditNodeAttributes();
    }

    onChangeAttribute(value, name) {
        return this.editNodeAttributes({ [name]: value });
    }
}
