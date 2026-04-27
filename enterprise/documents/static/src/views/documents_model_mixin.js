/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { user } from '@web/core/user';
import { useService } from "@web/core/utils/hooks";

export const DocumentsModelMixin = (component) =>
    class extends component {
        setup(params) {
            super.setup(...arguments);
            if (this.config.resModel === "documents.document") {
                this.originalSelection = params.state?.sharedSelection;
            }
            this.documentService = useService("document.document");
            this.initialLimit = 40;

            if (!this.defaultOrderBy?.length) {
                this.defaultOrderBy = [{ name: "create_date", asc: false }];
            }
        }

        exportSelection() {
            return this.root.selection.map((rec) => rec.resId);
        }

        /**
         * Also load the total file size
         * @override
         */
        async load() {
            const selection = this.root?.selection;
            if (!this.originalSelection && selection && selection.length > 0) {
                this.originalSelection = selection.map((rec) => rec.resId);
            }
            for (let arg of arguments) {
                arg.context['skip_res_field_check'] = true;
            }
            const res = await super.load(...arguments);
            if (this.config.resModel !== "documents.document") {
                return res;
            }
            this.env.searchModel.skipLoadClosePreview
                ? this.env.searchModel.skipLoadClosePreview = false
                : this.env.documentsView.bus.trigger("documents-close-preview");
            this._reapplySelection();
            this._computeFileSize();
            this.shortcutTargetRecords = this.orm.isSample ? [] : await this._loadShortcutTargetRecords();
            if (this.documentService.documentIdToRestore) {
                this.documentService.documentIdToRestore = undefined;
            }
            return res;
        }

        _reapplySelection() {
            const records = this.root.records;
            if (this.originalSelection && this.originalSelection.length > 0 && records) {
                const originalSelection = new Set(this.originalSelection);
                records.forEach((record) => {
                    record.selected = originalSelection.has(record.resId);
                });
                delete this.originalSelection;
            }
        }

        _computeFileSize() {
            let size = 0;
            if (this.root.groups) {
                size = this.root.groups.reduce((size, group) => {
                    return size + group.aggregates.file_size;
                }, 0);
            } else if (this.root.records) {
                size = this.root.records.reduce((size, rec) => {
                    return size + rec.data.file_size;
                }, 0);
            }
            size /= 1000 * 1000; // in MB
            this.fileSize = Math.round(size * 100) / 100;
        }

        async _loadShortcutTargetRecords() {
            const shortcuts = this.root.records.filter(
                (record) => !!record.data.shortcut_document_id,
            );
            if (!shortcuts.length) {
                return [];
            }
            const shortcutTargetRecords = [];
            const targetRecords = await this._loadRecords({
                ...this.config,
                resIds: shortcuts.map((record) => record.data.shortcut_document_id[0]),
            });
            for (const targetRecord of targetRecords) {
                shortcutTargetRecords.push(this._createRecordDatapoint(targetRecord));
            }
            return shortcutTargetRecords;
        }

        _createRecordDatapoint(data, mode = "readonly") {
            return new this.constructor.Record(
                this,
                {
                    context: this.config.context,
                    activeFields: this.config.activeFields,
                    resModel: this.config.resModel,
                    fields: this.config.fields,
                    resId: data.id || false,
                    resIds: data.id ? [data.id] : [],
                    isMonoRecord: true,
                    currentCompanyId: this.config.currentCompanyId,
                    mode,
                },
                data,
                { manuallyAdded: !data.id }
            );
        }
    };

let dataTransfer = null;

const setDataTransfer = (ev, name, value) => {
    dataTransfer = value;
    return ev.dataTransfer.setData(name, value);
}

export const DocumentsRecordMixin = (component) => class extends component {
    setup(config, data, options = {}) {
        super.setup(...arguments);
        if (data.id === this.model.documentService.documentIdToRestore) {
            this.selected = true;
        }
    }

    async update(changes, options = {}) {
        if ("name" in changes && !changes.name) {
            this.model.notification.add(_t("Name cannot be empty."), {
                type: "danger",
            });
            if (Object.keys(changes).length === 1) {
                this._discard();
                return;
            }
            delete changes.name;
            this._setEvalContext();
        }
        const modelMultiEdit = this.model.multiEdit;
        let movedRecordsIds = this.model.root.selection.map((rec) => rec.id);
        if (this.resId === this.model.documentService.previewedDocument?.record.resId) {
            // As previewed documents are not selected, force `save=true` to save any changes as the record is updated
            options.save = true;
            // Prevent multiEditing/moving the selection as it is not what we intend to modify when previewing.
            this.model.multiEdit = false;
            movedRecordsIds = [this.model.root.records.find((rec)=> rec.data.id === this.resId).id];
        }
        const originalFolderId = this.data.folder_id[0];
        const ret = await super.update(changes, options);
        if (this.data.folder_id && this.data.folder_id[0] !== originalFolderId) {
            this.model.root._removeRecords(movedRecordsIds);
            // Same as moving when not in preview
            this.model.env.documentsView.bus.trigger("documents-close-preview");
        }
        this.model.multiEdit = modelMultiEdit;
        return ret;
    }

    isPdf() {
        return this.data.mimetype === "application/pdf" || this.data.mimetype === "application/pdf;base64";
    }

    isRequest() {
        return !this.data.shortcut_document_id && this.data.type === "binary" && !this.data.attachment_id;
    }

    isShortcut() {
        return !!this.data.shortcut_document_id;
    }

    isURL() {
        return !this.data.shortcut_document_id && this.data.type === "url";
    }

    /**
     * Return the source Document if this is a shortcut and self if not.
     */
    get shortcutTarget() {
        if (!this.isShortcut()) {
            return this;
        }
        return this.model.shortcutTargetRecords.find(
            (rec) => rec.resId === this.data.shortcut_document_id[0],
        ) || this;
    }

    hasStoredThumbnail() {
        return this.data.thumbnail_status === "present";
    }

    isViewable() {
        const thisRecord = this.shortcutTarget;
        return (
            thisRecord.data.type !== "folder" &&
            ([
                "image/bmp",
                "image/gif",
                "image/jpeg",
                "image/png",
                "image/svg+xml",
                "image/tiff",
                "image/x-icon",
                "image/webp",
                "application/javascript",
                "application/json",
                "text/css",
                "text/html",
                "text/plain",
                "application/pdf",
                "application/pdf;base64",
                "audio/mpeg",
                "video/x-matroska",
                "video/mp4",
                "video/webm",
            ].includes(thisRecord.data.mimetype) ||
            (thisRecord.data.url && thisRecord.data.url.includes("youtu")))
        );
    }

    async onClickPreview(ev) {
        if (this.isRequest()) {
            ev.stopPropagation();
            // kanban view support
            ev.target.querySelector(".o_kanban_replace_document")?.click();
        } else if (this.isViewable()) {
            ev.stopPropagation();
            ev.preventDefault();
            const folder = this.model.env.searchModel
                .getFolders()
                .filter((folder) => folder.id === this.data.folder_id[0]);
            const hasPdfSplit =
                (!this.data.lock_uid || this.data.lock_uid[0] === user.userId) &&
                folder.user_permission === "edit";
            const selection = this.model.root.selection;
            const documents = selection.length > 1 && selection.find(rec => rec === this) && selection.filter(rec => rec.isViewable()) || [this];

            // Load the embeddedActions in case we open the split tool
            const embeddedActions = this.data.available_embedded_actions_ids?.records.map((rec) => ({ id: rec.resId, name: rec.data.display_name })) || [];

            await this.model.env.documentsView.bus.trigger("documents-open-preview", {
                documents,
                mainDocument: this,
                isPdfSplit: false,
                embeddedActions,
                hasPdfSplit,
            });
        } else if (this.isURL()) {
            window.open(this.data.url, "_blank");
        }
    }

    /**
     * Upon clicking on a record, if it is a file or if ctrl/shift is pressed,
     * we want to select it else we open the folder.
     */
    onRecordClick(ev, options = {}) {
        Object.assign(options, {
            isKeepSelection: options.isKeepSelection ?? (ev.ctrlKey || ev.metaKey),
            isRangeSelection: options.isRangeSelection ?? ev.shiftKey,
        });
        if (
            this.model.env.searchModel.getSelectedFolderId() === "TRASH" ||
            this.data.type !== "folder" ||
            options.isKeepSelection ||
            options.isRangeSelection
        ) {
            this.selectRecord(ev, options);
        } else {
            this.openFolder();
        }
    }

    openFolder() {
        const section = this.model.env.searchModel.getSections()[0];
        const target = this.isShortcut() ? this.shortcutTarget : this;
        const folderId = target.data.active ? target.data.id : "TRASH";
        this._ensureSearchPanelHasFolder(folderId).then(() => {
            this.model.env.searchModel.toggleCategoryValue(section.id, folderId);
            this.model.originalSelection = [this.shortcutTarget.resId];
            this.model.env.documentsView.bus.trigger("documents-expand-folder", { folderId: folderId });
        });
    }

    async _ensureSearchPanelHasFolder(folderId) {
        const folderInPanel = this.model.env.searchModel.getFolderById(folderId);
        if (!folderInPanel) {
            return this.model.env.searchModel._reloadSearchModel(true);
        }
    }

    /**
     * Selects records upon click if it is a file or ctrl/shift key is pressed.
     */
    selectRecord(ev, options = {}) {
        const { isKeepSelection, isRangeSelection } = options;

        const root = this.model.root;
        const anchor = root._documentsAnchor;
        if (!isRangeSelection || root.selection.length === 0) {
            root._documentsAnchor = this;
        }

        if (isRangeSelection && anchor) {
            const selectionDocumentIds = root.selection.map((r) => r.resId);
            const documentIds = Array.from(
                document.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)"),
            ).map((el) => parseInt(el.querySelector("div").dataset.id));
            const indexFrom = documentIds.indexOf(anchor.resId);
            const indexTo = documentIds.indexOf(this.resId);
            const lowerIdx = Math.min(indexFrom, indexTo);
            const upperIdx = Math.max(indexFrom, indexTo) + 1;

            const toSelectDocumentIds = [
                ...new Set([...selectionDocumentIds, ...documentIds.slice(lowerIdx, upperIdx)]),
            ];
            root.records.forEach((r) => {
                r.selected = r != this && toSelectDocumentIds.includes(r.resId);
            });
        } else if (!isKeepSelection) {
            root.selection.forEach((rec) => {
                rec.selected = false;
            });
        }
        this.toggleSelection();
    }

    async toggleSelection(selected) {
        await super.toggleSelection(selected);

        if (this.selected) {
            this.model.documentService.logAccess(this.data.access_token);
        }

        this.model.documentService.updateDocumentURL(null, this.model.root.selection);
    }

    /**
     * Jump to shortcut targeted file / open targeted folder.
     */
    jumpToTarget() {
        const section = this.model.env.searchModel.getSections()[0];
        let folderId;
        if (!this.shortcutTarget.data.active) {
            folderId = "TRASH";
        } else if (this.shortcutTarget.data.type === "folder") {
            // Using doc data shortcut_document_id because isContainer record does not (need to) load shortcutTarget.
            folderId = this.data.shortcut_document_id?.[0] || this.shortcutTarget.data.id;
        } else if (this.shortcutTarget.data.folder_id) {
            folderId = this.shortcutTarget.data.folder_id[0];
        } else if (this.shortcutTarget.data.owner_id[0] === this.model.documentService.store.odoobot.userId) {
            folderId = "COMPANY";
        } else if (this.shortcutTarget.data.owner_id[0] === user.userId) {
            folderId = "MY";
        }
        if (!folderId || !this.model.env.searchModel.getFolderById(folderId)) {
            folderId = "SHARED"; // Inaccessible folder
        }
        this.model.env.searchModel.toggleCategoryValue(section.id, folderId);
        this.model.originalSelection = [this.shortcutTarget.resId];
        this.model.env.documentsView.bus.trigger("documents-expand-folder", { folderId: folderId });
    }

    /**
     * Called when starting to drag kanban/list records
     */
    async onDragStart(ev) {
        const currentFolder = this.model.env.searchModel.getSelectedFolder();
        if (currentFolder.id === "TRASH") {
            ev.preventDefault();
            return this.model.notification.add(
                _t("You cannot move folders or files when in the trash."),
                { title: _t("Invalid operation"), type: "warning" }
            );
        }
        if (this.model.root.isDomainSelected) {
            ev.preventDefault();
            return this.model.notification.add(
                _t("Only current page items can be dragged."),
                { type: "info" }
            );
        }
        if (!this.selected) {
            this.model.root.selection.forEach((rec) => rec.selected = false);
            this.selected = true;
        }
        const root = this.model.root;
        const draggableRecords = root.selection.filter(
            (record) => (!record.data.lock_uid || record.data.lock_uid[0] === this.context.uid)
        );
        if (draggableRecords.length === 0) {
            ev.preventDefault();
            return;
        }
        const foldersById = Object.fromEntries(
            this.model.env.searchModel.getFolders().map((folder) => [folder.id, folder])
        );
        const movableRecords = draggableRecords.filter(
            (record) =>
                record.data.user_permission === "edit" &&
                (!record.data.folder_id ||
                    foldersById[record.data.folder_id[0]].user_permission === "edit"),
        );
        const nonMovableRecords = draggableRecords.filter(
            (record) => !movableRecords.includes(record),
        );
        const lockedCount = root.selection.reduce((count, record) => {
            return count + (record.data.lock_uid && record.data.lock_uid[0] !== this.context.uid);
        }, 0);
        const folderCount = draggableRecords.reduce((count, record) => {
            return count + (record.data.type === "folder");
        }, 0);
        const fileCount = draggableRecords.length - folderCount;
        setDataTransfer(
            ev,
            "o_documents_data",
            JSON.stringify({
                recordIds: draggableRecords.map((record) => record.resId),
                movableRecordIds: movableRecords.map((record) => record.resId),
                nonMovableRecordIds: nonMovableRecords.map((record) => record.resId),
                lockedCount,
            })
        );
        let dragText;
        if (draggableRecords.length === 1) {
            dragText = draggableRecords[0].data.name ? draggableRecords[0].data.display_name : _t("Unnamed");
        } else {
            let fileCountText, folderCountText;
            if (fileCount) {
                fileCountText = (fileCount.length === 1) ? _t("1 File") : _t("%s Files", fileCount);
            }
            if (folderCount) {
                folderCountText = (folderCount.length === 1) ? _t("1 Folder") : _t("%s Folders", folderCount);
            }
            dragText = fileCount ? fileCountText : "";
            dragText += folderCount ? fileCount ? " " + folderCountText : folderCountText : "";
        }
        if (lockedCount > 0) {
            dragText += _t(" (%s locked)", lockedCount);
        }
        const newElement = document.createElement("span");
        newElement.classList.add("o_documents_drag_icon");
        newElement.innerText = dragText;
        document.body.append(newElement);
        ev.dataTransfer.setDragImage(newElement, -5, -5);
        setTimeout(() => newElement.remove());
    }

//    TODO: Change the drag & drop with search panel
//    TODO: add notification when drop not valid
    async onDrop(ev) {
        if (!this.isValidDragTarget(ev)) {
            return;
        }
        if (this.data.user_permission != "edit") {
            return this.model.notification.add(
                _t("You don't have the rights to move documents nor create shortcut to that folder."),
                {
                    title: _t("Access Error"),
                    type: "warning",
                }
            );
        }
        if (!dataTransfer) {
            return;
        }
        const data = JSON.parse(dataTransfer);

        this.model.root.selection.forEach((rec) => rec.selected = false);
        await this.model.documentService.moveOrCreateShortcut(data, this.data.id, ev.ctrlKey);
        await this.model.env.searchModel._reloadSearchModel(true);
    
        dataTransfer = null;
    }

    isValidDragTarget(_ev) {
        if (!dataTransfer) {
            return false;
        }
        const data = JSON.parse(dataTransfer); // can only be accessed from the drop event... shitty news...
        return this.data.type == "folder" && !data.recordIds.includes(this.resId);
    }
};
