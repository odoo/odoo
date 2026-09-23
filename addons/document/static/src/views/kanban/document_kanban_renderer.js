/** @odoo-module native */
import { useCommand } from "@web/ui/commands";
import {
    FileUploadProgressContainer,
    FileUploadProgressKanbanRecord,
} from "@web/components/file_upload";
import { _t } from "@web/core/translation";
import { KanbanRenderer } from "@web/views/kanban";

import { DocumentsRightPanel } from "@document/components/document_right_panel/document_right_panel";
import { DocumentsRendererMixin } from "@document/views/document_renderer_mixin";
import { DocumentsActionHelper } from "@document/views/helper/document_action_helper";
import { DocumentsDropZone } from "@document/views/helper/document_drop_zone";
import { DocumentsFileViewerHost } from "@document/views/helper/document_file_viewer";
import { DocumentsKanbanRecord } from "@document/views/kanban/document_kanban_record";

import { onMounted } from "@odoo/owl";

export class DocumentsKanbanRenderer extends DocumentsRendererMixin(KanbanRenderer) {
    static props = [...KanbanRenderer.props, "previewStore"];
    static template = "document.DocumentsKanbanRenderer";
    static components = Object.assign({}, KanbanRenderer.components, {
        DocumentsDropZone,
        FileUploadProgressContainer,
        FileUploadProgressKanbanRecord,
        KanbanRecord: DocumentsKanbanRecord,
        DocumentsActionHelper,
        DocumentsFileViewerHost,
        DocumentsRightPanel,
    });

    static recordSelector = ".o_kanban_record";
    static focusSelector = (resId) => `.o_kanban_record[data-value-id="${resId}"]`;
    static dropTargetSelector = ".o_kanban_record.o_folder_record";

    setup() {
        super.setup();
        useCommand(
            _t("Toggle favorite"),
            async () => {
                if (this.selection.length) {
                    await this.env.model.orm.call(
                        "document.document",
                        "action_toggle_user_favorite",
                        [this.selection.map((record) => record.resId)],
                    );
                    await this.env.model.load();
                }
            },
            {
                category: "smart_action",
                hotkey: "alt+t",
            },
        );

        onMounted(() => {
            if (this.isMobile && this.isRecentFolder) {
                this.root.el.classList.add("o_documents_recent");
            }
        });
    }

    onGlobalClick(ev) {
        if (ev.target.closest(".o_kanban_record:not(.o_kanban_ghost)")) {
            return;
        }
        this.documentService.focusRecord(this.getContainerRecord());
        this.props.list.selection.forEach((el) => el.toggleSelection(false));
    }

    /**
     * @override
     */
    focusNextCard(area, direction) {
        const cards = area.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)");
        if (!cards.length) {
            return;
        }
        let cardsPerRow = 0;
        const allCards = area.querySelectorAll(".o_kanban_record");
        const firstCardClientTop = allCards[0].getBoundingClientRect().top;
        for (const card of allCards) {
            if (card.getBoundingClientRect().top === firstCardClientTop) {
                cardsPerRow++;
            } else {
                break;
            }
        }
        const focusedCardIdx = [...cards].indexOf(document.activeElement);
        let newIdx = focusedCardIdx;
        const folderCount = this.folderCount();
        if (direction === "up") {
            const oldIdx = newIdx;
            newIdx -= cardsPerRow;
            if (newIdx < folderCount && oldIdx >= folderCount) {
                if ((oldIdx - folderCount) % cardsPerRow >= folderCount % cardsPerRow) {
                    newIdx = folderCount - 1;
                } else {
                    newIdx =
                        folderCount -
                        ((folderCount % cardsPerRow) -
                            ((oldIdx - folderCount) % cardsPerRow));
                }
            }
        } else if (direction === "down") {
            const oldIdx = newIdx;
            newIdx += cardsPerRow;
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
            newIdx -= 1;
        } else if (direction === "right") {
            newIdx += 1;
        }
        if (
            newIdx >= 0 &&
            newIdx < cards.length &&
            cards[newIdx] instanceof HTMLElement
        ) {
            const focusedCard = cards[newIdx];
            focusedCard.focus();
            const record = this.props.list.records.find(
                (e) => e.id === focusedCard.dataset.id,
            );
            if (record) {
                this.documentService.focusRecord(record);
            }
            return true;
        }
    }

    folderCount() {
        return this.props.list.records.reduce(
            (count, record) => (record.data.type === "folder" ? count + 1 : count),
            0,
        );
    }

    hasFolders() {
        return this.props.list.records.some((record) => record.data.type === "folder");
    }

    hasFiles() {
        return this.props.list.records.some((record) => record.data.type !== "folder");
    }

    get isRecentFolder() {
        const groupBy = this.env.model.config.groupBy;
        return groupBy?.length === 1 && groupBy[0] === "last_access_date_group";
    }

    get isMobile() {
        return this.env.isSmall;
    }

    getFolderRecords() {
        return this.props.list.records
            .filter((record) => record.data.type === "folder")
            .map((record) => ({ record, key: record.id }));
    }

    /**
     * @override
     */
    getGroupsOrRecords() {
        if (this.props.list.isGrouped) {
            return super.getGroupsOrRecords();
        }
        return this.props.list.records
            .filter((record) => record.data.type !== "folder")
            .map((record) => ({ record, key: record.id }));
    }

    toggleRangeSelection(record) {
        if (!this.lastCheckedRecord) {
            return;
        }
        const { records } = this.props.list;
        const documentIds = Array.from(
            this.root.el?.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)") ||
                [],
        ).map((el) => el.dataset.id);
        const recordIndex = documentIds.indexOf(record.id);
        const lastCheckedRecordIndex = documentIds.indexOf(this.lastCheckedRecord.id);
        const start = Math.min(recordIndex, lastCheckedRecordIndex);
        const end = Math.max(recordIndex, lastCheckedRecordIndex);
        const toSelectDocumentIds = documentIds.slice(start, end + 1);
        records.forEach((r) => {
            if (toSelectDocumentIds.includes(r.id)) {
                r.toggleSelection(!record.selected);
            }
        });
    }

    toggleSelection(record) {
        const isSelection = record && !record.selected;
        super.toggleSelection(...arguments);
        if (isSelection) {
            this.documentService.focusRecord(record, true);
        }
    }
}
