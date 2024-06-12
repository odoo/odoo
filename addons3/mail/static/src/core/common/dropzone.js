/* @odoo-module */

import { Component, useEffect, useRef, useState } from "@odoo/owl";

export class Dropzone extends Component {
    static props = {
        extraClass: { type: String, optional: true },
        onDrop: { type: Function, optional: true },
        ref: Object,
    };
    static template = "mail.Dropzone";

    setup() {
        this.root = useRef("root");
        this.state = useState({
            isDraggingInside: false,
        });
        useEffect(() => {
            const { top, left, width, height } = this.props.ref.el.getBoundingClientRect();
            this.root.el.style = `top:${top}px;left:${left}px;width:${width}px;height:${height}px;`;
        });
    }
}
