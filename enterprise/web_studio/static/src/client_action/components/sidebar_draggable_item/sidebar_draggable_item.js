/** @odoo-module */
import { Component } from "@odoo/owl";

export class SidebarDraggableItem extends Component {
    static template = "web_studio.SidebarDraggableItem";
    static props = {
        className: { type: String, optional: true },
        description: { type: String, optional: true },
        dropData: { optional: true },
        string: { type: String },
        structure: { type: String },
    };
}
