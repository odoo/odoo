import { Component } from "@odoo/owl";

export class ElementToolboxContainer extends Component {
    static template = "mysterious_egg.ElementToolboxContainer";
    static props = {
        title: String,
        slots: { type: Object, optional: true },
    };
}
