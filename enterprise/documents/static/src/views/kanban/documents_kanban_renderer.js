/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

import { useBus, useService } from "@web/core/utils/hooks";
import { DocumentsDropZone } from "../helper/documents_drop_zone";
import { FileUploadProgressContainer } from "@web/core/file_upload/file_upload_progress_container";
import { FileUploadProgressKanbanRecord } from "@web/core/file_upload/file_upload_progress_record";
import { DocumentsRendererMixin } from "@documents/views/documents_renderer_mixin";
import { DocumentsKanbanRecord } from "./documents_kanban_record";
import { DocumentsActionHelper } from "../helper/documents_action_helper";
import { DocumentsFileViewer } from "../helper/documents_file_viewer";
import { DocumentsDetailsPanel } from "@documents/components/documents_details_panel/documents_details_panel";
import { useCommand } from "@web/core/commands/command_hook";
import { onMounted, useRef } from "@odoo/owl";
import { DocumentsChatter } from "@documents/views/chatter/documents_chatter";

export class DocumentsKanbanRenderer extends DocumentsRendererMixin(KanbanRenderer) {
    static props = [...KanbanRenderer.props, "previewStore"];
    static template = "documents.DocumentsKanbanRenderer";
    static components = Object.assign({}, KanbanRenderer.components, {
        DocumentsDropZone,
        FileUploadProgressContainer,
        FileUploadProgressKanbanRecord,
        KanbanRecord: DocumentsKanbanRecord,
        DocumentsActionHelper,
        DocumentsFileViewer,
        DocumentsDetailsPanel,
        Chatter: DocumentsChatter,
    });

    setup() {
        super.setup();
        this.root = useRef("root");
        const { uploads } = useService("file_upload");
        this.documentUploads = uploads;
        this.documentService = useService("document.document");

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
            async () => {
                if (this.targetRecords.length) {
                    await this.env.model.orm.call("documents.document", "toggle_favorited_multi", [
                        this.targetRecords.map((record) => record.resId),
                    ]);
                    this.env.model.load();
                }
            },
            {
                category: "smart_action",
                hotkey: "alt+t",
            }
        );
        useBus(this.documentService.bus, "DOCUMENT_ACTIVITY_CHANGED", ({ detail }) => {
            if (
                this.targetRecords.length == 1 &&
                this.targetRecords[0].data.id == detail.recordId
            ) {
                this.render(true); // Re-render this Component and its children on activity add/edit/unlink
            }
        });
        onMounted(() => {
            if (this.isMobile && this.isRecentFolder) {
                this.root.el.classList.add('o_documents_recent');
            }
        });
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
        const cards = area.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)");
        if (!cards.length) {
            return;
        }
        // Find out how many cards there are per row.
        let cardsPerRow = 0;
        // For the calculation we need all cards (kanban ghost included)
        const allCards = area.querySelectorAll(".o_kanban_record");
        const firstCardClientTop = allCards[0].getBoundingClientRect().top;
        for (const card of allCards) {
            if (card.getBoundingClientRect().top === firstCardClientTop) {
                cardsPerRow++;
            } else {
                break;
            }
        }
        // Find out current x and y of the active card.
        const focusedCardIdx = [...cards].indexOf(document.activeElement);
        let newIdx = focusedCardIdx; // up
        const folderCount = this.folderCount();
        if (direction === "up") {
            const oldIdx = newIdx;
            newIdx -= cardsPerRow; // up
            if (newIdx < folderCount && oldIdx >= folderCount) {
                if ((oldIdx - folderCount) % cardsPerRow >= folderCount % cardsPerRow) {
                    newIdx = folderCount - 1;
                } else {
                    newIdx = folderCount - ((folderCount % cardsPerRow) - (oldIdx - folderCount) % cardsPerRow);
                }
            }
        } else if (direction === "down") {
            const oldIdx = newIdx;
            newIdx += cardsPerRow; // down
            if (newIdx >= cards.length) {
                newIdx = cards.length - 1;
            }
            if (oldIdx < folderCount && newIdx >= folderCount) {
                if (oldIdx % cardsPerRow >= folderCount % cardsPerRow) {
                    newIdx = folderCount - 1;
                } else {
                    newIdx = folderCount + (oldIdx % cardsPerRow);
                }
            }
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

    folderCount() {
        return this.props.list.records
            .reduce((count, record) => (record.data.type === 'folder' ? count + 1: count), 0);
    }

    hasFolders() {
        return this.props.list.records.some((record) => record.data.type === 'folder');
    }

    hasFiles() {
        return this.props.list.records.some((record) => record.data.type !== 'folder');
    }

    get isRecentFolder() {
        const groupBy = this.env.model.config.groupBy;
        return groupBy?.length === 1 && groupBy[0] === "last_access_date_group";
    }

    get isMobile() {
        return this.env.isSmall;
    }

    /**
     * Return documents.document with type 'folder'
     */
    getFolderRecords() {
        return this.props.list.records
            .filter((record) => record.data.type === 'folder')
            .map((record) => ({ record, key: record.id}));
    }

    /**
     * Return documents.document with type different from 'folder'
     *
     * @override
     */
    getGroupsOrRecords() {
        if (this.props.list.isGrouped) {
            return super.getGroupsOrRecords();
        }
        return this.props.list.records
            .filter((record) => record.data.type !== 'folder')
            .map((record) => ({ record, key: record.id }));
    }
}
