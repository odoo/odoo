import { Component } from "@odoo/owl";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";

export class MenuProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.Menu";
    static components = {
        Property,
        SidebarPropertiesToolbox,
    };
    static props = {
        node: { type: Object },
    };
    get colorPicker() {
        return this.env.viewEditorModel.controllerProps.arch.querySelector(
            "field[widget=kanban_color_picker]"
        );
    }
    editColorPicker() {
        this.env.viewEditorModel.activeNodeXpath = this.colorPicker.getAttribute("studioXpath");
    }
}
