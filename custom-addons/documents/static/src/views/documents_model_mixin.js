/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { inspectorFields } from "./inspector/documents_inspector";
import { makeActiveField } from "@web/model/relational_model/utils";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export const DocumentsModelMixin = (component) =>
    class extends component {
        /**
         * Add inspector fields to the list of fields to load
         * @override
         */
        setup(params) {
            for (const field of inspectorFields) {
                if (!(field in params.config.activeFields)) {
                    if (field === 'folder_id') {
                        // force required to true for that field, to have proper validation inside the inspector
                        params.config.activeFields[field] = makeActiveField({ required: true });
                    } else {
                        params.config.activeFields[field] = makeActiveField();
                    }
                }
            }
            params.config.activeFields.available_rule_ids = Object.assign(
                {},
                params.config.activeFields.available_rule_ids,
                {
                    related: {
                        activeFields: {
                            display_name: makeActiveField(),
                            note: makeActiveField(),
                            limited_to_single_record: makeActiveField(),
                            create_model: makeActiveField(),
                        },
                        fields: {
                            display_name: {
                                type: "string",
                            },
                            note: {
                                type: "string",
                            },
                            limited_to_single_record: {
                                type: "boolean",
                            },
                            create_model: {
                                type: "string",
                            },
                        },
                    },
                }
            );
            super.setup(...arguments);
            if (this.config.resModel === "documents.document") {
                this.originalSelection = params.state?.sharedSelection;
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
            if (selection && selection.length > 0) {
                this.originalSelection = selection.map((rec) => rec.resId);
            }
            const res = await super.load(...arguments);
            if (this.config.resModel !== "documents.document") {
                return res;
            }
            this.env.documentsView.bus.trigger("documents-close-preview");
            this._reapplySelection();
            this._computeFileSize();
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
    };

export const DocumentsRecordMixin = (component) => class extends component {

    async update() {
        const originalFolderId = this.data.folder_id[0];
        await super.update(...arguments);
        if (this.data.folder_id && this.data.folder_id[0] !== originalFolderId) {
            this.model.root._removeRecords(this.model.root.selection.map((rec) => rec.id));
        }
    }

    isPdf() {
        return this.data.mimetype === "application/pdf" || this.data.mimetype === "application/pdf;base64";
    }

    hasThumbnail() {
        return this.data.thumbnail_status === "present";
    }

    isViewable() {
        return (
            [
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
            ].includes(this.data.mimetype) ||
            (this.data.url && this.data.url.includes("youtu"))
        );
    }

    /**
     * Upon clicking on a record, we want to select it and unselect other records.
     */
    onRecordClick(ev, options = {}) {
        if (this.model.env.inDialog) {
            ev.preventDefault();
            return;
        }
        const isKeepSelection =
            options.isKeepSelection !== undefined ? options.isKeepSelection : ev.ctrlKey || ev.metaKey;
        const isRangeSelection = options.isRangeSelection !== undefined ? options.isRangeSelection : ev.shiftKey;

        const root = this.model.root;
        const anchor = root._documentsAnchor;
        if (!isRangeSelection || root.selection.length === 0) {
            root._documentsAnchor = this;
        }

        // Make sure to keep the record if we were in a multi select
        const isMultiSelect = root.selection.length > 1;
        let thisSelected = !this.selected;
        if (isRangeSelection && anchor) {
            const indexFrom = root.records.indexOf(root.records.find((rec) => rec.resId === anchor.resId));
            const indexTo = root.records.indexOf(this);
            const lowerIdx = Math.min(indexFrom, indexTo);
            const upperIdx = Math.max(indexFrom, indexTo) + 1;
            root.selection.forEach((rec) => (rec.selected = false));
            for (let idx = lowerIdx; idx < upperIdx; idx++) {
                root.records[idx].selected = true;
            }
            thisSelected = true;
        } else if (!isKeepSelection && (isMultiSelect || thisSelected)) {
            root.selection.forEach((rec) => {
                rec.selected = false;
            });
            thisSelected = undefined;
        }
        this.toggleSelection(thisSelected);
    }

    /**
     * Called when starting to drag kanban/list records
     */
    async onDragStart(ev) {
        if (this.model.env.inDialog) {
            ev.preventDefault();
            return;
        }
        if (!this.selected) {
            this.onRecordClick(ev, { isKeepSelection: false, isRangeSelection: false });
        }
        const root = this.model.root;
        const foldersById = this.model.env.searchModel.getFolders().reduce((agg, folder) => {
            agg[folder.id] = folder;
            return agg;
        }, {});
        const draggableRecords = root.selection.filter(
            (record) => (!record.data.lock_uid || record.data.lock_uid[0] === this.context.uid) && foldersById[record.data.folder_id[0]].has_write_access
        );
        if (draggableRecords.length === 0) {
            ev.preventDefault();
            return;
        }
        const lockedCount = draggableRecords.reduce((count, record) => {
            return count + (record.data.lock_uid && record.data.lock_uid[0] !== this.context.uid);
        }, 0);
        ev.dataTransfer.setData(
            "o_documents_data",
            JSON.stringify({
                recordIds: draggableRecords.map((record) => record.resId),
                lockedCount,
            })
        );
        let dragText;
        if (draggableRecords.length === 1) {
            dragText = draggableRecords[0].data.name ? draggableRecords[0].data.display_name : _t("Unnamed");
        } else if (lockedCount > 0) {
            dragText = _t("%s Documents (%s locked)", draggableRecords.length, lockedCount);
        } else {
            dragText = _t("%s Documents", draggableRecords.length);
        }
        const newElement = document.createElement("span");
        newElement.classList.add("o_documents_drag_icon");
        newElement.innerText = dragText;
        document.body.append(newElement);
        ev.dataTransfer.setDragImage(newElement, -5, -5);
        setTimeout(() => newElement.remove());
    }

    async openDeleteConfirmationDialog(root, callback, isPermanent) {
        const dialogProps = {
            title: isPermanent ? _t("Delete permanently") : _t("Move to trash"),
            body: isPermanent ? root.isDomainSelected || root.selection.length > 1
                ? _t("Are you sure you want to permanently erase the documents?")
                : _t("Are you sure you want to permanently erase the document?")
                : _t("Items moved to the trash will be deleted forever after %s days.", 
                    this.model.env.searchModel.deletionDelay
                    ),
            confirmLabel: isPermanent ? _t("Delete permanently") : _t("Move to trash"),
            cancelLabel: _t("Discard"),
            confirm: async () => {
                await callback();
                await this.model.env.documentsView.bus.trigger("documents-close-preview");
            },
            cancel: () => {},
        };
        this.model.dialog.add(ConfirmationDialog, dialogProps);
    }
};
