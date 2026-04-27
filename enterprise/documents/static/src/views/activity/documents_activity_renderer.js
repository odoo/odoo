/** @odoo-module **/

import { ActivityRenderer } from "@mail/views/web/activity/activity_renderer";

import { DocumentsFileViewer } from "../helper/documents_file_viewer";

import { useRef } from "@odoo/owl";

export class DocumentsActivityRenderer extends ActivityRenderer {
    static props = {
        ...ActivityRenderer.props,
        previewStore: Object,
    };
    static template = "documents.DocumentsActivityRenderer";
    static components = {
        ...ActivityRenderer.components,
        DocumentsFileViewer,
    };

    setup() {
        super.setup();
        this.root = useRef("root");
    }

    getDocumentsAttachmentViewerProps() {
        return { previewStore: this.props.previewStore };
    }
}
