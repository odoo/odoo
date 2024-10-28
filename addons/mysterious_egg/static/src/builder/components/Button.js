import { Component, useState } from "@odoo/owl";

export class Button extends Component {
    static template = "mysterious_egg.Button";
    static props = {
        id: { type: String, optional: true },
        label: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },
        onClick: { type: Function, optional: true },
    };

    setup() {
        this.activeState = useState(this.env.buttonMetadatas.activeState || {});
        this.isActive = this.env.buttonMetadatas.isActive;
        this.onClick = this.env.buttonMetadatas.onClick;
        this.onMouseenter = this.env.buttonMetadatas.onMouseenter;
        this.onMouseleave = this.env.buttonMetadatas.onMouseleave;
    }
}
