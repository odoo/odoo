/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ListRenderer } from "@web/views/list/list_renderer";

import { useService } from "@web/core/utils/hooks";
import { DocumentsInspector } from "../inspector/documents_inspector";
import { FileUploadProgressContainer } from "@web/core/file_upload/file_upload_progress_container";
import { FileUploadProgressDataRow } from "@web/core/file_upload/file_upload_progress_record";
import { DocumentsDropZone } from "../helper/documents_drop_zone";
import { DocumentsActionHelper } from "../helper/documents_action_helper";
import { DocumentsFileViewer } from "../helper/documents_file_viewer";
import { DocumentsListRendererCheckBox } from "./documents_list_renderer_checkbox";
import { useCommand } from "@web/core/commands/command_hook";
import { useRef } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

export class DocumentsListRenderer extends ListRenderer {
    static props = [...ListRenderer.props, "inspectedDocuments", "previewStore"];
    static template = "documents.DocumentsListRenderer";
    static recordRowTemplate = "documents.DocumentsListRenderer.RecordRow";
    static components = Object.assign({}, ListRenderer.components, {
        DocumentsInspector,
        DocumentsListRendererCheckBox,
        FileUploadProgressContainer,
        FileUploadProgressDataRow,
        DocumentsDropZone,
        DocumentsActionHelper,
        DocumentsFileViewer,
    });

    setup() {
        super.setup();
        this.root = useRef("root");
        const { uploads } = useService("file_upload");
        this.documentUploads = uploads;
        useCommand(
            _t("Select all"),
            () => {
                const allSelected =
                    this.props.list.selection.length === this.props.list.records.length;
                this.props.list.records.forEach((record) => {
                    record.toggleSelection(!allSelected);
                });
            },
            {
                category: "smart_action",
                hotkey: "control+a",
            }
        );
    }

    getDocumentsAttachmentViewerProps() {
        return { previewStore: this.props.previewStore };
    }

    getDocumentsInspectorProps() {
        const documents = this.props.inspectedDocuments.length
            ? this.props.inspectedDocuments
            : this.props.list.selection;
        const documentsIds = documents.map((doc) => doc.resId);
        return {
            documents: this.props.list.records.filter((rec) => documentsIds.includes(rec.resId)),
            count: this.props.list.model.useSampleModel ? 0 : this.props.list.count,
            fileSize: this.props.list.model.fileSize,
            fields: this.props.list.fields,
            archInfo: this.props.archInfo,
        };
    }

    /**
     * Called when a keydown event is triggered.
     */
    onGlobalKeydown(ev) {
        if (ev.key !== "Enter" && ev.key !== " ") {
            return;
        }
        const row = ev.target.closest(".o_data_row");
        const record = row && this.props.list.records.find((rec) => rec.id === row.dataset.id);
        if (!record) {
            return;
        }
        const options = {};
        if (ev.key === " ") {
            options.isKeepSelection = true;
        }
        ev.stopPropagation();
        ev.preventDefault();
        record.onRecordClick(ev, options);
    }

    /**
     * There's a custom behavior on cell clicked as we (un)select the row (see record.onRecordClick)
     */
    onCellClicked(record, column, ev) {
        if (this.env.inDialog) {
            ev.stopPropagation();
            super.onCellClicked(record, column, ev);
        }
    }

    /**
     * Called when a click event is triggered.
     */
    onGlobalClick(ev) {
        // We have to check that we are indeed clicking in the list view as on mobile,
        // the inspector renders above the renderer but it still triggers this event.
        if (ev.target.closest(".o_data_row") || !ev.target.closest(".o_list_renderer")) {
            return;
        }
        this.props.list.selection.forEach((el) => el.toggleSelection(false));
    }

    onCellKeydown(ev, group = null, record = null) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "enter") {
            return;
        }
        return super.onCellKeydown(...arguments);
    }

    get hasSelectors() {
        return this.props.allowSelectors;
    }
}
