import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { Component, proxy } from "@odoo/owl";

export class Dropzone extends Component {
    static props = {
        extraClass: { type: String, optional: true },
        onDrop: { type: Function, optional: true },
        ref: [Object, Function],
        slots: { type: Object, optional: true },
    };
    static template = "web.Dropzone";

    setup() {
        super.setup();
        this.root = useRef("root");
        this.state = proxy({
            isDraggingInside: false,
        });
        useLayoutEffect(() => {
            const getEl =
                typeof this.props.ref === "function" ? this.props.ref : () => this.props.ref.el;
            const { top, left, width, height } = getEl().getBoundingClientRect();
            this.root.el.style = `top:${top}px;left:${left}px;width:${width}px;height:${height}px;`;
        });
    }
}
