/** @odoo-module **/

import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { DocumentsKanbanCompiler } from "./documents_kanban_compiler";
import { FileUploadProgressBar } from "@web/core/file_upload/file_upload_progress_bar";
import { useBus, useService } from "@web/core/utils/hooks";
import { xml } from "@odoo/owl";

const CANCEL_GLOBAL_CLICK = ["a", ".dropdown", ".oe_kanban_action"].join(",");

export class DocumentsKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        // File upload
        const { bus, uploads } = useService("file_upload");
        this.documentUploads = uploads;
        useBus(bus, "FILE_UPLOAD_ADDED", (ev) => {
            if (ev.detail.upload.data.get("document_id") == this.props.record.resId) {
                this.render(true);
            }
        });

        // Pdf Thumbnail
        this.pdfService = useService("documents_pdf_thumbnail");
        this.pdfService.enqueueRecords([this.props.record]);
    }

    /**
     * @override
     */
    getRecordClasses() {
        let result = super.getRecordClasses();
        if (this.props.record.selected) {
            result += " o_record_selected";
        }
        if (this.props.record.data.type === "empty") {
            result += " oe_file_request";
        }
        return result;
    }

    /**
     * Get the current file upload for this record if there is any
     */
    getFileUpload() {
        return Object.values(this.documentUploads).find(
            (upload) => upload.data.get("document_id") == this.props.record.resId
        );
    }

    /**
     * @override
     */
    onGlobalClick(ev) {
        if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            return;
        }
        // Preview is clicked
        if (ev.target.closest("div[name='document_preview']")) {
            this.props.record.onClickPreview(ev);
            if (ev.cancelBubble) {
                return;
            }
        }
        const options = {};
        if (ev.target.classList.contains("o_record_selector")) {
            options.isKeepSelection = true;
        }
        this.props.record.onRecordClick(ev, options);
    }

    onKeydown(ev) {
        if (ev.key !== "Enter" && ev.key !== " ") {
            return;
        }
        ev.preventDefault();
        const options = {};
        if (ev.key === " ") {
            options.isKeepSelection = true;
        }
        return this.props.record.onRecordClick(ev, options);
    }
}
DocumentsKanbanRecord.components = {
    ...KanbanRecord.components,
    FileUploadProgressBar,
};
DocumentsKanbanRecord.defaultProps = {
    ...KanbanRecord.defaultProps,
    Compiler: DocumentsKanbanCompiler,
};

DocumentsKanbanRecord.template = xml`
    <div
        role="article"
        t-att-class="getRecordClasses()"
        t-att-data-id="props.canResequence and props.record.id"
        t-att-tabindex="props.record.model.useSampleModel ? -1 : 0"
        t-on-click.synthetic="onGlobalClick"
        t-on-keydown.synthetic="onKeydown"
        t-ref="root">
        <t t-call="{{ templates[this.constructor.KANBAN_BOX_ATTRIBUTE] }}" t-call-context="this.renderingContext"/>
    </div>`;
