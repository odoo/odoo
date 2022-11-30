/** @odoo-module **/

import { Component, onMounted, useExternalListener, useRef, useState } from "@odoo/owl";

export class Dropzone extends Component {
    setup() {
        // Prevents to browser to open or download the file when it is dropped
        // outside of the dropzone.
        useExternalListener(window, "dragover", (ev) => ev.preventDefault());
        useExternalListener(window, "drop", (ev) => ev.preventDefault());

        this.root = useRef("root");
        this.state = useState({ isDraggingInside: false });
        this.dragCount = 0;

        onMounted(() => {
            const { top, left, width, height } = this.props.ref.el.getBoundingClientRect();
            Object.assign(this.root.el.style, {
                top: `${top}px`,
                left: `${left}px`,
                width: `${width}px`,
                height: `${height}px`,
            });
        });
    }

    onDragEnter(ev) {
        if (this.dragCount === 0) {
            this.state.isDraggingInside = true;
        }
        this.dragCount++;
    }

    onDragLeave(ev) {
        this.dragCount--;
        if (this.dragCount === 0) {
            this.state.isDraggingInside = false;
        }
    }

    onDrop(ev) {
        this.state.isDraggingInside = false;
    }
}

Object.assign(Dropzone, {
    template: "mail.dropzone",
    props: { ref: Object },
});
