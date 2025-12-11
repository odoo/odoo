import { Component } from "@odoo/owl";

export class BuilderOptionsSection extends Component {
    static template = "html_builder.BuilderOptionsSection";
    static props = {
        title: { type: String, optional: true },
        containerClass: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
}
