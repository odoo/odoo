/** @odoo-module **/

import { Dropzone } from "@mail/new/dropzone/dropzone";

import { Component, useExternalListener, useState, xml } from "@odoo/owl";

export class DropzoneContainer extends Component {
    setup() {
        this.isDraggingFile = false;
        this.dragCount = 0;
        this.state = useState({
            isDraggingFile: false,
        });
        useExternalListener(document, "dragenter", this.onDragEnter);
        useExternalListener(document, "dragleave", this.onDragLeave);
        useExternalListener(document, "drop", this.onDrop);
    }

    onDragEnter(ev) {
        if (this.dragCount === 0 && ev.dataTransfer && ev.dataTransfer.types.includes("Files")) {
            this.state.isDraggingFile = true;
        }
        this.dragCount++;
    }

    onDragLeave(ev) {
        this.dragCount--;
        if (this.dragCount === 0) {
            this.state.isDraggingFile = false;
        }
    }

    onDrop(ev) {
        this.state.isDraggingFile = false;
        this.dragCount = 0;
    }
}

Object.assign(DropzoneContainer, {
    components: { Dropzone },
    props: { dropzones: Object },
    template: xml`
        <t t-if="state.isDraggingFile">
            <t t-foreach="[...props.dropzones]" t-as="dropzone" t-key="dropzone.id">
                <Dropzone ref="dropzone.ref"/>
            </t>
        </t>
    `,
});
