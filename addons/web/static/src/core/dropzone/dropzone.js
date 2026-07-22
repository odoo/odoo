import { useLayoutEffect } from "@web/owl2/utils";
import { Component, proxy, signal, t, useProps } from "@odoo/owl";

export const dropzoneProps = {
    extraClass: t.string().optional(),
    onDrop: t.function().optional(),
    ref: t.or([t.object(), t.function()]),
    slots: t.object().optional(),
};

export class Dropzone extends Component {
    props = useProps(dropzoneProps);
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
