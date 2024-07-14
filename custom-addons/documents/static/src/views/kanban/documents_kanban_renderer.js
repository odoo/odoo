/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

import { useService } from "@web/core/utils/hooks";
import { DocumentsDropZone } from "../helper/documents_drop_zone";
import { DocumentsInspector } from "../inspector/documents_inspector";
import { FileUploadProgressContainer } from "@web/core/file_upload/file_upload_progress_container";
import { FileUploadProgressKanbanRecord } from "@web/core/file_upload/file_upload_progress_record";
import { DocumentsKanbanRecord } from "./documents_kanban_record";
import { DocumentsActionHelper } from "../helper/documents_action_helper";
import { DocumentsFileViewer } from "../helper/documents_file_viewer";
import { useCommand } from "@web/core/commands/command_hook";
import { useRef } from "@odoo/owl";

export class DocumentsKanbanRenderer extends KanbanRenderer {
    static props = [...KanbanRenderer.props, "inspectedDocuments", "previewStore"];
    static template = "documents.DocumentsKanbanRenderer";
    static components = Object.assign({}, KanbanRenderer.components, {
        DocumentsInspector,
        DocumentsDropZone,
        FileUploadProgressContainer,
        FileUploadProgressKanbanRecord,
        KanbanRecord: DocumentsKanbanRecord,
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
        useCommand(
            _t("Toggle favorite"),
            () => {
                if (this.props.list.selection.length) {
                    this.props.list.selection[0].update({
                        is_favorited: !this.props.list.selection[0].data.is_favorited,
                    });
                }
            },
            {
                category: "smart_action",
                hotkey: "alt+t",
            }
        );
    }

    /**
     * Called when clicking in the kanban renderer.
     */
    onGlobalClick(ev) {
        // Only when clicking in empty space
        if (ev.target.closest(".o_kanban_record:not(.o_kanban_ghost)")) {
            return;
        }
        this.props.list.selection.forEach((el) => el.toggleSelection(false));
    }

    /**
     * Focus next card with proper support for up and down arrows.
     *
     * @override
     */
    focusNextCard(area, direction) {
        // We do not need to support groups as it is disabled for this view.
        const cards = area.querySelectorAll(".o_kanban_record");
        if (!cards.length) {
            return;
        }
        // Find out how many cards there are per row.
        let cardsPerRow = 0;
        const firstCardClientTop = cards[0].getBoundingClientRect().top;
        for (const card of cards) {
            if (card.getBoundingClientRect().top === firstCardClientTop) {
                cardsPerRow++;
            } else {
                break;
            }
        }
        // Find out current x and y of the active card.
        const focusedCardIdx = [...cards].indexOf(document.activeElement);
        let newIdx = focusedCardIdx; // up
        if (direction === "up") {
            newIdx -= cardsPerRow; // up
        } else if (direction === "down") {
            newIdx += cardsPerRow; // down
        } else if (direction === "left") {
            newIdx -= 1; // left
        } else if (direction === "right") {
            newIdx += 1; // right
        }
        if (newIdx >= 0 && newIdx < cards.length && cards[newIdx] instanceof HTMLElement) {
            cards[newIdx].focus();
            return true;
        }
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
            archInfo: this.props.archInfo,
            fields: this.props.list.fields,
        };
    }
}
