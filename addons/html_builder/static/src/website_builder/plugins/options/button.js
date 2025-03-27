import { Component } from "@odoo/owl";

export class Button extends Component {
    static template = "html_builder.Button";
    static props = {
        label: { type: String, optional: true },
        title: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },
        onClick: Function,
        isActive: { Boolean, optional: true },
    };
}
