/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { DocumentsKanbanCompiler } from "./documents_kanban_compiler";
import { FileUploadProgressBar } from "@web/core/file_upload/file_upload_progress_bar";
import { useBus, useService } from "@web/core/utils/hooks";
import { useState, xml } from "@odoo/owl";

const CANCEL_GLOBAL_CLICK = ["a", ".dropdown", ".oe_kanban_action"].join(",");
const COMPANY_ROOT_OWNER_ID = 1;

export class DocumentsKanbanRecord extends KanbanRecord {
    static components = {
        ...KanbanRecord.components,
        FileUploadProgressBar,
    };
    static defaultProps = {
        ...KanbanRecord.defaultProps,
        Compiler: DocumentsKanbanCompiler,
    };
    static template = xml`
        <div
            role="article"
            t-att-class="getRecordClasses()"
            t-att-data-id="props.canResequence and props.record.id"
            t-att-tabindex="props.record.model.useSampleModel ? -1 : 0"
            t-on-click.synthetic="onGlobalClick"
            t-on-dragenter.stop.prevent="onDragEnter"
            t-on-dragover.prevent="onDragOver"
            t-on-dragleave.stop.prevent="onDragLeave"
            t-on-drop.stop.prevent="onDrop"
            t-on-keydown.synthetic="onKeydown"
            t-ref="root">
            <t t-call="{{ templates[this.constructor.KANBAN_CARD_ATTRIBUTE] }}" t-call-context="this.renderingContext"/>
        </div>`;
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
        this.drag = useState({ state: "none" });

        // Pdf Thumbnail
        this.pdfService = useService("documents_pdf_thumbnail");
        this.pdfService.enqueueRecords([this.props.record]);

        // Activity updates from Chatter
        this.documentService = useService("document.document");
        useBus(this.documentService.bus, "DOCUMENT_CHATTER_ACTIVITY_CHANGED", ({ detail }) => {
            if (this.props.record.data.id == detail.recordId) {
                this.props.record.load();
            }
        });
    }

    /**
     * @override
     */
    getRecordClasses() {
        let result = super.getRecordClasses();
        if (this.props.record.selected) {
            result += " o_record_selected";
        }
        if (this.props.record.isRequest()) {
            result += " oe_file_request";
        }
        if (this.props.record.data.type == "folder") {
            result += " o_folder_record";
        }
        if (this.drag.state === "hover") {
            result += " o_drag_hover";
        } else if (this.drag.state === "invalid") {
            result += " o_drag_invalid";
        }
        if (
            this.env.isSmall &&
            this.props.list.groupByField?.name == "last_access_date_group"
        ) {
            result += " flex-grow-1";
        }
        return result;
    }

    get renderingContext() {
        const context = super.renderingContext;
        context.encodeURIComponent = encodeURIComponent;

        if ([false, "TRASH", "RECENT"].includes(this.env.searchModel.getSelectedFolderId())) {
            context.inFolder = this.props.record.data.folder_id?.[1] ||
                (
                    this.props.record.data?.owner_id[0] === user.userId
                    ? _t("My Drive")
                    : this.props.record.data?.owner_id[0] === COMPANY_ROOT_OWNER_ID
                        ? _t("Company")
                        : _t("Shared with me")
                );
        }
        context.mimetype = this.props.record.shortcutTarget.data.mimetype;
        return context;
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
        this.props.record.onRecordClick(ev);
    }

    onKeydown(ev) {
        if (ev.key !== "Enter" && ev.key !== " ") {
            return;
        }
        ev.preventDefault();
        const options = {};
        if (ev.key === "Enter" && this.props.record.data.type !== "folder") {
            this.props.record.onClickPreview(ev);
        } else if (ev.key === " ") {
            options.isKeepSelection = true;
        }
        return this.props.record.onRecordClick(ev, options);
    }

    onDragEnter(ev) {
        if (this.props.record.data.type !== "folder") {
            return;
        }
        if (!ev.dataTransfer.types.includes("o_documents_data")) {
            return;
        }
        const isInvalidFolder = this.props.list.selection
            .map((r) => r.data.id)
            .includes(this.props.record.data.id);
        this.drag.state = isInvalidFolder ? "invalid" : "hover";
        const icon = this.rootRef.el.querySelector(".fa-folder-o");
        icon?.classList.remove("fa-folder-o");
        icon?.classList.add("fa-folder-open-o");
    }

    onDragOver(ev) {
        const isInvalidTarget =
            this.props.record.data.type !== "folder" ||
            this.props.list.selection.map((r) => r.data.id).includes(this.props.record.data.id);
        const dropEffect = isInvalidTarget ? "none" : ev.ctrlKey ? "link" : "move";
        ev.dataTransfer.dropEffect = dropEffect;
    }

    onDragLeave(ev) {
        // we do this since the dragleave event is fired when hovering a child
        const elemBounding = this.rootRef.el.getBoundingClientRect();
        const isOutside =
            ev.clientX < elemBounding.left ||
            ev.clientX > elemBounding.right ||
            ev.clientY < elemBounding.top ||
            ev.clientY > elemBounding.bottom;
        if (!isOutside) {
            return;
        }
        if (this.props.record.data.type !== "folder") {
            return;
        }
        this.drag.state = "none";
        const icon = this.rootRef.el.querySelector(".fa-folder-open-o");
        icon?.classList.remove("fa-folder-open-o");
        icon?.classList.add("fa-folder-o");
    }

    onDrop(ev) {
        this.drag.state = "none";
        const icon = this.rootRef.el.querySelector(".fa-folder-open-o");
        icon?.classList.remove("fa-folder-open-o");
        icon?.classList.add("fa-folder-o");
    }
}
