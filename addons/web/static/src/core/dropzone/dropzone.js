import { Component, onMounted, onPatched, proxy, signal, t, useProps } from "@odoo/owl";

export const dropzoneProps = {
    extraClass: t.string().optional(),
    onDrop: t.function().optional(),
    ref: t.signal(t.ref()),
    slots: t.object().optional(),
};

export class Dropzone extends Component {
    props = useProps(dropzoneProps);
    static template = "web.Dropzone";

    root = signal.ref();

    setup() {
        super.setup();
        this.state = proxy({
            isDraggingInside: false,
        });
        const alignWithTarget = () => {
            const { top, left, width, height } = this.props.ref().getBoundingClientRect();
            this.root().style = `top:${top}px;left:${left}px;width:${width}px;height:${height}px;`;
        };
        onMounted(alignWithTarget);
        onPatched(alignWithTarget);
    }
}
