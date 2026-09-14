/** @odoo-module native */
import { getCommonEmbeddedActions } from "@document/views/utils";
import {
    DETAIL_PANEL_REQUIRED_FIELDS,
    preSuperSetup,
    useDocumentView,
} from "@document/views/hooks";
import { makeActiveField } from "@web/model/relational_model";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/collections/objects";
import { prepareStaticActionMenuItems } from "@web/views/view_utils";
import { onWillDestroy, onWillRender, useRef, useState, useSubEnv } from "@odoo/owl";

export const DocumentsControllerMixin = (component) =>
    class extends component {
        /**
         * Selector of the DOM elements standing for the selected documents in
         * this view, read by the file previewer; null when the view has none.
         */
        static selectedDocumentsSelector = null;

        setup() {
            preSuperSetup();
            super.setup(...arguments);
            this.searchBarToggler = useSearchBarToggler();
            useSubEnv({
                searchBarToggler: this.searchBarToggler,
            });

            this.documentService = useService("document.document");
            this.firstLoadSelectId = this.documentService.initData?.documentId;
            this.uploadFileInputRef = useRef("uploadFileInput");
            Object.assign(this, useDocumentView(this.documentsViewHelpers()));
            this.documentStates = useState({ previewStore: {} });
            this.rightPanelState = useState(this.documentService.rightPanelReactive);

            // Registered synchronously: the control panel's DocumentsAction reads
            // it from its own mounted effect, which runs before this component's.
            const provider = () => ({
                getTopbarActions: () => this.getTopBarActionMenuItems(),
                getMenuProps: () => this.actionMenuProps,
            });
            this.documentService.selectionActions.provider = provider;
            onWillDestroy(() => {
                // On a view switch the next controller has already registered its own.
                if (this.documentService.selectionActions.provider === provider) {
                    this.documentService.selectionActions.provider = null;
                }
            });

            onWillRender(() => this.openInitialPreview());
        }

        get hasSelectedRecords() {
            return this.targetRecords.length;
        }

        get targetRecords() {
            return this.model.targetRecords;
        }

        documentsViewHelpers() {
            return {
                getSelectedDocumentsElements: () => {
                    const selector = this.constructor.selectedDocumentsSelector;
                    return (
                        (selector && this.root?.el?.querySelectorAll(selector)) || []
                    );
                },
                setPreviewStore: (previewStore) => {
                    this.documentStates.previewStore = previewStore;
                },
                isRecordPreviewable: this.isRecordPreviewable.bind(this),
            };
        }

        isRecordPreviewable(record) {
            return record.isViewable();
        }

        openInitialPreview() {
            if (!this.firstLoadSelectId) {
                return;
            }
            const initData = this.documentService.initData;
            const doc = this.model.root.records.find(
                (record) => record.data.id === this.firstLoadSelectId,
            );
            if (doc) {
                this.firstLoadSelectId = false;
                doc.selected = true;
                if (initData.openPreview) {
                    initData.openPreview = false;
                    this.env.searchModel.skipLoadClosePreview = true;
                    doc.onClickPreview(new Event("click"));
                }
            }
        }

        get modelParams() {
            const modelParams = super.modelParams;
            modelParams.multiEdit = true;

            const activeFields = Object.keys(modelParams.config.activeFields);

            DETAIL_PANEL_REQUIRED_FIELDS.forEach((field) => {
                if (!activeFields.includes(field)) {
                    modelParams.config.activeFields[field] = makeActiveField();
                }
            });

            if (!activeFields.includes("res_id")) {
                modelParams.config.activeFields.res_id = makeActiveField();
                modelParams.config.activeFields.res_id.related = {
                    fields: {
                        display_name: {
                            name: "display_name",
                            type: "char",
                        },
                    },
                    activeFields: {
                        display_name: makeActiveField(),
                    },
                };
            }

            if (!activeFields.includes("tag_ids")) {
                modelParams.config.activeFields.tag_ids = makeActiveField();
                modelParams.config.activeFields.tag_ids.related = {
                    activeFields: {
                        display_name: makeActiveField({ readonly: true }),
                        color: makeActiveField(),
                    },
                    fields: {
                        display_name: {
                            name: "display_name",
                            type: "char",
                            readonly: true,
                        },
                        color: {
                            name: "color",
                            type: "integer",
                            readonly: false,
                        },
                    },
                };
            }

            if (!activeFields.includes("alias_tag_ids")) {
                modelParams.config.activeFields.alias_tag_ids = {
                    ...modelParams.config.activeFields.tag_ids,
                };
            }

            return modelParams;
        }

        getEmbeddedActions() {
            const embeddedActions = getCommonEmbeddedActions(this.model.targetRecords);
            return Object.fromEntries(
                embeddedActions.map((e) => [
                    e.id,
                    {
                        description: e.name,
                        callback: () => this.model.onDoAction(e.id),
                        groupNumber: COG_GROUP.ACTIONS,
                    },
                ]),
            );
        }

        getTopBarActionMenuItems() {
            const embeddedActions = this.getEmbeddedActions();
            const userIsInternal = this.documentService.userIsInternal;
            return {
                ...embeddedActions,
                download: {
                    isAvailable: () => this.targetRecords.some((r) => !r.isRequest()),
                    sequence: 10,
                    description: _t("Download"),
                    icon: "fa-solid fa-download",
                    callback: () => this.model.onDownload(),
                    groupNumber: COG_GROUP.DATA,
                },
                share: {
                    isAvailable: () => userIsInternal && this.targetRecords.length > 0,
                    sequence: 10,
                    description: _t("Share…"),
                    icon: "fa-solid fa-share-nodes",
                    callback: () => this.model.onShare(),
                    groupNumber: COG_GROUP.RECORD,
                },
            };
        }

        getStaticActionMenuItems() {
            const selectionCount = this.targetRecords.length;
            const userIsInternal = this.documentService.userIsInternal;
            const singleSelection = selectionCount === 1 && this.targetRecords[0];
            const isInTrash = this.env.searchModel.getSelectedFolderId() === "TRASH";
            const editMode = this.targetRecords.every(
                (r) => r.data.user_permission === "edit",
            );
            const someActive = this.targetRecords.some((r) => r.data.active);
            const someArchived = this.targetRecords.some((r) => !r.data.active);
            const someUnlocked = this.targetRecords.some((r) => !r.data.lock_uid);
            const menuItems = super.getStaticActionMenuItems();
            const topBarActions = this.env.isSmall
                ? this.getTopBarActionMenuItems()
                : {};
            return {
                ...omit(menuItems, "archive", "delete", "duplicate", "unarchive"),
                ...topBarActions,
                ...prepareStaticActionMenuItems({
                    duplicate: {
                        isAvailable: () => this.model.canDuplicateRecords,
                        callback: () => this.model.onDuplicate(),
                    },
                    delete: {
                        isAvailable: () => this.model.canDeleteRecords,
                        callback: () => this.model.onDelete(),
                    },
                }),
                copy: {
                    isAvailable: () => selectionCount && !isInTrash,
                    sequence: 30,
                    description: _t("Copy Links"),
                    icon: "fa-solid fa-link",
                    callback: () => this.model.onCopyLinks(),
                    groupNumber: COG_GROUP.DATA,
                },
                rename: {
                    isAvailable: () =>
                        editMode && singleSelection && someUnlocked && !isInTrash,
                    sequence: 20,
                    description: _t("Rename…"),
                    icon: "fa-regular fa-pen-to-square",
                    callback: () => this.model.onRename(),
                    groupNumber: COG_GROUP.RECORD,
                },
                move: {
                    isAvailable: () => this.model.canMoveRecords,
                    sequence: 25,
                    description: _t("Move…"),
                    icon: "fa-solid fa-right-to-bracket",
                    callback: () => this.model.onMove(),
                    groupNumber: COG_GROUP.RECORD,
                },
                shortcut: {
                    isAvailable: () => userIsInternal && !isInTrash,
                    sequence: 35,
                    description: _t("Add Shortcut…"),
                    icon: "fa-solid fa-up-right-from-square",
                    callback: () => this.model.onCreateShortcut(),
                    groupNumber: COG_GROUP.RECORD,
                },
                details: {
                    isAvailable: () =>
                        userIsInternal &&
                        !this.env.searchModel.context.documents_view_secondary,
                    sequence: 50,
                    description: _t("Info & Tags"),
                    icon: "fa-solid fa-circle-info",
                    callback: () => this.model.onToggleRightPanel(),
                    groupNumber: COG_GROUP.RECORD,
                },
                version: {
                    isAvailable: () => this.model.canManageVersions,
                    sequence: 55,
                    description: _t("Manage Versions…"),
                    icon: "fa-solid fa-clock-rotate-left",
                    callback: () => this.model.onManageVersions(),
                    groupNumber: COG_GROUP.RECORD,
                },
                trash: {
                    isAvailable: () =>
                        userIsInternal && editMode && someActive && someUnlocked,
                    sequence: 80,
                    description: _t("Move to Trash"),
                    icon: "fa-regular fa-trash-can",
                    callback: () => this.model.onArchive(),
                    groupNumber: COG_GROUP.RECORD,
                },
                restore: {
                    isAvailable: () => someArchived,
                    sequence: 85,
                    description: _t("Restore"),
                    icon: "fa-solid fa-trash-arrow-up",
                    callback: () => this.model.onRestore(),
                    groupNumber: COG_GROUP.RECORD,
                },
                lock: {
                    isAvailable: () =>
                        userIsInternal &&
                        singleSelection &&
                        singleSelection.data.type !== "folder" &&
                        !isInTrash &&
                        editMode,
                    sequence: 45,
                    description: singleSelection?.data?.lock_uid
                        ? _t("Unlock")
                        : _t("Lock"),
                    icon: singleSelection?.data?.lock_uid
                        ? "fa-solid fa-lock-open"
                        : "fa-solid fa-lock",
                    callback: () => this.model.onToggleLock(),
                    groupNumber: COG_GROUP.RECORD,
                },
                pdf: {
                    isAvailable: () =>
                        userIsInternal &&
                        selectionCount &&
                        editMode &&
                        this.targetRecords.every(
                            (record) => record.isPdf() && !record.data.lock_uid,
                        ) &&
                        !isInTrash,
                    sequence: 10,
                    description: singleSelection ? _t("Split PDF…") : _t("Merge PDFs…"),
                    icon: "fa-solid fa-scissors",
                    callback: () => this.model.onSplitPDF(),
                    groupNumber: COG_GROUP.APP,
                },
            };
        }

        get showActions() {
            const previewing = !!this.rightPanelState.previewedDocument;
            const focusing = !!this.rightPanelState.focusedRecord;
            const focusedSelected =
                focusing &&
                !!this.targetRecords.find(
                    (r) => r.id === this.rightPanelState.focusedRecord.id,
                );
            return !previewing && (!focusing || focusedSelected);
        }
    };
