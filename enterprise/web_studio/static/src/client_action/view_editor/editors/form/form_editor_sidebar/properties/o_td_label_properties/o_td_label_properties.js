/** @odoo-module */

import { Component } from "@odoo/owl";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";

export class OTdLabelProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.OTdLabelProperties";
    static components = { SidebarPropertiesToolbox };
    static props = ["node"];
}
