/** @odoo-module **/

import { ActivityRenderer } from "@mail/views/web/activity/activity_renderer";

import { DocumentsInspector } from "../inspector/documents_inspector";
import { DocumentsFileViewer } from "../helper/documents_file_viewer";

import { useRef } from "@odoo/owl";

export class DocumentsActivityRenderer extends ActivityRenderer {
    static props = {
        ...ActivityRenderer.props,
        inspectedDocuments: Array,
        previewStore: Object,
    };
    static template = "documents.DocumentsActivityRenderer";
    static components = {
        ...ActivityRenderer.components,
        DocumentsFileViewer,
        DocumentsInspector,
    };

    setup() {
        super.setup();
        this.root = useRef("root");
    }

    getDocumentsAttachmentViewerProps() {
        return { previewStore: this.props.previewStore };
    }

    /**
     * Props for documentsInspector
     */
    getDocumentsInspectorProps() {
        return {
            documents: this.props.records.filter((rec) => rec.selected),
            count: this.props.records.length,
            fileSize: this.env.model.fileSize,
            archInfo: this.props.archInfo,
            fields: this.props.fields,
        };
    }
}
