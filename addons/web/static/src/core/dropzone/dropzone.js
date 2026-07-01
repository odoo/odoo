import { useLayoutEffect } from "@web/owl2/utils";
import { Component, proxy, signal } from "@odoo/owl";

export class Dropzone extends Component {
    static props = {
        extraClass: { type: String, optional: true },
        onDrop: { type: Function, optional: true },
        ref: [Object, Function],
        slots: { type: Object, optional: true },
    };
    static template = "web.Dropzone";

    root = signal(null);

    setup() {
        super.setup();
        this.state = proxy({
            isDraggingInside: false,
        });
        useLayoutEffect(() => {
            const getEl =
                typeof this.props.ref === "function" ? this.props.ref : () => this.props.ref.el;
            const { top, left, width, height } = getEl().getBoundingClientRect();
            this.root().style = `top:${top}px;left:${left}px;width:${width}px;height:${height}px;`;
        });
    }
}
