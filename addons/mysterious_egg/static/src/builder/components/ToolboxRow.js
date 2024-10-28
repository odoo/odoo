import { Component } from "@odoo/owl";

export class ToolboxRow extends Component {
    static template = "mysterious_egg.ToolboxRow";
    static props = {
        label: String,
        slots: { type: Object, optional: true },
    };
}
