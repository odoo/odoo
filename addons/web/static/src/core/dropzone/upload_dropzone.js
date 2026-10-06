import { Component, onMounted, onPatched, signal, t, useProps } from "@odoo/owl";

/**
 * Dropzone of the upload buttons, looking like the one of Google Drive: the
 * area is outlined and a hint is shown at its bottom.
 */
export class UploadDropzone extends Component {
    static template = "web.UploadDropzone";
    props = useProps({
        label: t.string().optional(),
        onDrop: t.function(),
        ref: t.function(),
    });

    root = signal.ref();

    setup() {
        const alignWithTarget = () => {
            const rect = this.props.ref().getBoundingClientRect();
            // the visible part of the target: its hint stays on screen when the target is taller
            const top = Math.max(rect.top, 0);
            const bottom = Math.min(rect.bottom, window.innerHeight);
            this.root().style = `top:${top}px;left:${rect.left}px;width:${rect.width}px;height:${
                bottom - top
            }px;`;
        };
        onMounted(alignWithTarget);
        onPatched(alignWithTarget);
    }

    onDrop(ev) {
        ev.preventDefault();
        this.props.onDrop([...ev.dataTransfer.files]);
    }
}
