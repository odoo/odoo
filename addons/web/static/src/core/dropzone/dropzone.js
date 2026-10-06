import { Component, computed, onMounted, onPatched, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class Dropzone extends Component {
    static template = "web.Dropzone";
    props = useProps({
        extraClass: t.string().optional(),
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

    hint = computed(() =>
        this.props.label
            ? _t("Drop files to upload them to %s", this.props.label)
            : _t("Drop files to upload them")
    );

    onDrop(ev) {
        ev.preventDefault();
        this.props.onDrop([...ev.dataTransfer.files]);
    }
}
