/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ListRenderer } from "@web/views/list/list_renderer";

import { useService } from "@web/core/utils/hooks";
import { FileUploadProgressContainer } from "@web/core/file_upload/file_upload_progress_container";
import { FileUploadProgressDataRow } from "@web/core/file_upload/file_upload_progress_record";
import { DocumentsDropZone } from "../helper/documents_drop_zone";
import { DocumentsActionHelper } from "../helper/documents_action_helper";
import { DocumentsFileViewer } from "../helper/documents_file_viewer";
import { DocumentsRendererMixin } from "@documents/views/documents_renderer_mixin";
import { DocumentsListRendererCheckBox } from "./documents_list_renderer_checkbox";
import { DocumentsDetailsPanel } from "@documents/components/documents_details_panel/documents_details_panel";
import { useCommand } from "@web/core/commands/command_hook";
import { useRef } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Chatter } from "@mail/chatter/web_portal/chatter";

export class DocumentsListRenderer extends DocumentsRendererMixin(ListRenderer) {
    static props = [...ListRenderer.props, "previewStore"];
    static template = "documents.DocumentsListRenderer";
    static recordRowTemplate = "documents.DocumentsListRenderer.RecordRow";
    static components = Object.assign({}, ListRenderer.components, {
        DocumentsListRendererCheckBox,
        FileUploadProgressContainer,
        FileUploadProgressDataRow,
        DocumentsDropZone,
        DocumentsActionHelper,
        DocumentsFileViewer,
        DocumentsDetailsPanel,
        Chatter,
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

    /**
     * Called when a keydown event is triggered.
     */
    onGlobalKeydown(ev) {
        if (ev.key !== "Enter" && ev.key !== " " || this.editedRecord) {
            return;
        }
        const row = ev.target.closest(".o_data_row");
        const record = row && this.props.list.records.find((rec) => rec.id === row.dataset.id);
        if (!record) {
            return;
        }
        if (ev.key === "Enter" && record.data.type !== "folder") {
            record.onClickPreview(ev);
        }
        ev.stopPropagation();
        ev.preventDefault();
        this.toggleRecordSelection(record);
    }

    /**
     * Upon clicking on a record, opens the folder/preview the file.
     * If ctrl or shift key pressed, selects/unselects the record.
     * If the column is editable, the record is selected and click
     * without ctrl or shift pressed, edits the column.
     */
    onCellClicked(record, column, ev) {
        ev.stopPropagation();
        const isSelectionKeyPressed = ev.ctrlKey || ev.metaKey || ev.shiftKey;
        if (isSelectionKeyPressed) {
            this.toggleRecordSelection(record);
        } else if (record.selected && this.editableColumns.includes(column.name)) {
            return super.onCellClicked(...arguments);
        } else if (record.data.type !== "folder") {
            return record.onClickPreview(ev);
        } else {
            record.openFolder();
        }
    }

    get editableColumns() {
        return ["name", "tag_ids", "partner_id", "owner_id", "company_id", "folder_id"];
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
        if (ev.target.closest(".o_documents_view thead")) {
            return; // We then have to check that we are not clicking on the header
        }
        this.props.list.selection.forEach((el) => el.toggleSelection(false));
    }

    getFolderInfo() {
        return {
            count: this.props.list.model.useSampleModel ? 0 : this.props.list.count,
            fileSize: this.props.list.model.fileSize,
        };
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

    get isMobile() {
        return this.env.isSmall;
    }

    onDragEnter(ev) {
        const row = ev.target.closest(".o_data_row");
        const record = row && this.props.list.records.find((rec) => rec.id === row.dataset.id);
        if (record.data.type !== "folder") {
            return;
        }
        if (record.selected) {
            row.classList.remove("table-info");
        }
        const isInvalidFolder = this.props.list.selection
            .map((r) => r.data.id)
            .includes(record.data.id);
        row.classList.add(isInvalidFolder ? "table-danger" : "table-success");
    }

    onDragLeave(ev) {
        const row = ev.target.closest(".o_data_row");
        // we do this since the dragleave event is fired when hovering a child
        const elemBounding = row.getBoundingClientRect();
        const isOutside =
            ev.clientX < elemBounding.left ||
            ev.clientX > elemBounding.right ||
            ev.clientY < elemBounding.top ||
            ev.clientY > elemBounding.bottom;
        if (!isOutside) {
            return;
        }
        const record = row && this.props.list.records.find((rec) => rec.id === row.dataset.id);
        if (record.data.type !== "folder") {
            return;
        }
        if (record.selected) {
            row.classList.add("table-info");
        }
        row.classList.remove("table-success", "table-danger");
    }

    onDragOver(ev) {
        const row = ev.target.closest(".o_data_row");
        const record = row && this.props.list.records.find((rec) => rec.id === row.dataset.id);
        const isInvalidTarget =
            record.data.type !== "folder" ||
            this.props.list.selection.map((r) => r.data.id).includes(record.data.id);
        const dropEffect = isInvalidTarget ? "none" : ev.ctrlKey ? "link" : "move";
        ev.dataTransfer.dropEffect = dropEffect;
    }

    onDrop(ev) {
        const row = ev.target.closest(".o_data_row");
        const record = row && this.props.list.records.find((rec) => rec.id === row.dataset.id);
        if (record.data.type !== "folder") {
            return;
        }
        row.classList.remove("table-success", "table-danger");
        record.onDrop(ev);
    }
}
