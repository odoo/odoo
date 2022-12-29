/* @odoo-module */

import { Component, useRef, useState, useEffect } from "@odoo/owl";

export class Dropzone extends Component {
    static props = { ref: Object, onDrop: { type: Function, optional: true } };
    static template = "mail.dropzone";

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
