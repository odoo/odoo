/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PromoteStudioAutomationDialog } from "@web_enterprise/webclient/promote_studio_dialog/promote_studio_dialog";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useBus, useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { useSetupAction } from "@web/search/action_hook";
import { DocumentsPermissionPanel } from "@documents/components/documents_permission_panel/documents_permission_panel";
import { PdfManager } from "@documents/owl/components/pdf_manager/pdf_manager";
import { EventBus, onMounted, onWillStart, markup, useComponent, useEnv, useRef, useSubEnv } from "@odoo/owl";

// TODO: clean in master
import { loadMaxUploadSize as loadMaxUploadSizeDocumentService } from "@documents/core/document_service";
export const loadMaxUploadSize = loadMaxUploadSizeDocumentService;

/**
 * Controller/View hooks
 */

export function openDeleteConfirmationDialog(model, isPermanent) {
    return new Promise((resolve, reject) => {
        const root = model.root;
        const dialogProps = {
            title: isPermanent ? _t("Delete permanently") : _t("Move to trash"),
            body: isPermanent
                ? root.isDomainSelected || root.selection.length > 1
                    ? _t("Are you sure you want to permanently erase the documents?")
                    : _t("Are you sure you want to permanently erase the document?")
                : _t(
                      "Items moved to the trash will be deleted forever after %s days.",
                      model.env.searchModel.deletionDelay
                  ),
            confirmLabel: isPermanent ? _t("Delete permanently") : _t("Move to trash"),
            cancelLabel: _t("Discard"),
            confirm: async () => {
                resolve(true);
            },
            cancel: () => {
                resolve(false);
            },
        };
        model.dialog.add(ConfirmationDialog, dialogProps);
    });
}

export async function toggleArchive(model, resModel, resIds, doArchive) {
    if (doArchive && !(await openDeleteConfirmationDialog(model, false))) {
        return;
    }
    const action = await model.orm.call(
        resModel,
        doArchive ? "action_archive" : "action_unarchive",
        [resIds]
    );
    if (action && Object.keys(action).length !== 0) {
        model.action.doAction(action);
    }
    if (doArchive) {
        await model.env.documentsView.bus.trigger("documents-close-preview");
    }
}

export function preSuperSetupFolder() {
    const component = useComponent();
    const orm = useService("orm");
    onWillStart(async () => {
        component._deletionDelay = await orm.call("documents.document", "get_deletion_delay", [[]]);
    });
}

/**
 * To be executed before calling super.setup in view controllers.
 */
export function preSuperSetup() {
    // Otherwise not available in model.env
    useSubEnv({
        documentsView: {
            bus: new EventBus(),
        },
    });
    const component = useComponent();
    const props = component.props;
    // Root state is shared between views to keep the selection
    if (props.globalState && props.globalState.sharedSelection) {
        if (!props.state) {
            props.state = {};
        }
        if (!props.state.modelState) {
            props.state.modelState = {};
        }
        props.state.modelState.sharedSelection = props.globalState.sharedSelection;
    }
}

/**
 * Sets up the env required by documents view, as well as any other hooks.
 * Returns properties to be applied to the calling component. The code assumes that those properties are assigned to the component.
 */
export function useDocumentView(helpers) {
    const component = useComponent();
    const props = component.props;
    const root = useRef("root");
    const orm = useService("orm");
    const notification = useService("notification");
    const dialogService = useService("dialog");
    const action = useService("action");
    const documentService = useService("document.document");

    // Env setup
    useSubEnv({
        model: component.model,
    });
    const env = useEnv();
    const bus = env.documentsView.bus;

    // Opens Share Dialog
    const _openShareDialog = async ({ id, shortcut_document_id }) => {
        const document = shortcut_document_id ? { id: shortcut_document_id[0] } : { id };
        dialogService.add(DocumentsPermissionPanel, {
            document,
            onChangesSaved: () => env.searchModel.trigger("update"),
        });
    };

    // Open Automation rules
    const _openAutomations = async ({ folderId, folderDisplayName }) => {
        const checkBaseAutomation = await orm.searchCount("ir.module.module", [
            ["name", "=", "base_automation"],
            ["state", "=", "installed"],
        ]);
        if (!checkBaseAutomation > 0) {
            return dialogService.add(PromoteStudioAutomationDialog, {
                title: _t("Odoo Studio - Customize workflows in minutes"),
            });
        }
        const userHasAccessRight = await user.checkAccessRight("base.automation", "create");
        if (!userHasAccessRight) {
            return notification.add(_t("Contact your Administrator to get access if needed."), {
                title: _t("Access to Automations"),
                type: "info",
            });
        }
        const documentsModelId = await orm.search(
            "ir.model",
            [["model", "=", "documents.document"]],
            { limit: 1 }
        );
        return await action.doAction("base_automation.base_automation_act", {
            additionalContext: {
                active_test: false,
                default_model_id: documentsModelId[0],
                search_default_model_id: documentsModelId[0],
                default_name: _t("Put in %s", folderDisplayName),
                default_filter_domain: [["folder_id", "in", [folderId]]],
                default_trigger: "on_create_or_write",
            },
        });
    };

    // Keep selection between views
    useSetupAction({
        rootRef: root,
        getGlobalState: () => ({
            sharedSelection: component.model.exportSelection(),
        }),
    });

    useBus(bus, "documents-open-share", (ev) => {
        _openShareDialog(ev.detail);
    });

    useBus(bus, "documents-open-automations", (ev) => {
        _openAutomations(ev.detail);
    });

    onWillStart(async () => {
        component.isDocumentsManager = await user.hasGroup("documents.group_documents_manager");
    });

    onMounted(async() => {
        documentService.updateDocumentURLRefresh();
    });

    return {
        // Refs
        root,
        // Services
        orm,
        notification,
        dialogService,
        actionService: action,
        // Document preview
        ...useDocumentsViewFilePreviewer(helpers),
        // Document upload
        canUploadInFolder: (folder) => documentService.canUploadInFolder(folder),
        ...useDocumentsViewFileUpload(),
        // Trigger rule
        ...useEmbeddedAction(),
        // Helpers
        hasShareDocuments: () => {
            const folder = env.searchModel.getSelectedFolder();
            const selectedRecords = env.model.root.selection.length;
            return typeof folder.id !== "number" && !selectedRecords;
        },
        userIsInternal: documentService.userIsInternal,
        userIsDocumentManager: documentService.userIsDocumentManager,
        // Listeners
        onClickDocumentsRequest: () => {
            action.doAction("documents.action_request_form", {
                additionalContext: {
                    default_partner_id: props.context.default_partner_id || false,
                    default_folder_id:
                        env.searchModel.getSelectedFolderId() || env.searchModel.getFolders()[1].id,
                    default_res_id: props.context.default_res_id || false,
                    default_res_model: props.context.default_res_model || false,
                    default_requestee_id: props.context.default_partner_id || false,
                },
                fullscreen: env.isSmall,
                onClose: async () => {
                    await env.model.load();
                    env.model.useSampleModel = env.model.root.records.length === 0;
                    env.model.notify();
                },
            });
        },
        onClickDocumentsAddUrl: () => {
            const folderId = env.searchModel.getSelectedFolderId();
            action.doAction("documents.action_url_form", {
                additionalContext: {
                    default_type: "url",
                    default_partner_id: props.context.default_partner_id || false,
                    default_folder_id: env.searchModel.getSelectedFolderId(),
                    default_res_id: props.context.default_res_id || false,
                    default_res_model: props.context.default_res_model || false,
                    ...(folderId === "COMPANY"
                        ? { default_owner_id: documentService.store.odoobot.userId }
                        : {}),
                },
                fullscreen: env.isSmall,
                onClose: async () => {
                    await env.model.load();
                    env.model.useSampleModel = env.model.root.records.length === 0;
                    env.model.notify();
                },
            });
        },
        onClickAddFolder: () => {
            const currentFolder = env.searchModel.getSelectedFolderId();
            action.doAction("documents.action_folder_form", {
                additionalContext: {
                    default_type: "folder",
                    default_folder_id: currentFolder || false,
                    ...(currentFolder === "COMPANY"
                        ? {
                              default_access_internal: "edit",
                              default_owner_id: documentService.store.odoobot.userId,
                          }
                        : {}),
                },
                fullscreen: env.isSmall,
                onClose: async () => {
                    await env.searchModel._reloadSearchModel(true);
                    bus.trigger("documents-expand-folder", {
                        folderId: [false, "COMPANY"].includes(currentFolder) ? "MY" : currentFolder,
                    });
                },
            });
        },
        onClickShareFolder: async () => {
            if (env.model.root.selection.length > 0) {
                if (env.model.root.selection.length !== 1) {
                    return;
                }
                const rec = env.model.root.selection[0];
                await _openShareDialog({
                    id: rec.resId,
                    name: rec._values.name,
                    shortcut_document_id: rec._values.shortcut_document_id,
                });
            } else {
                const folder = env.searchModel.getSelectedFolder();
                await _openShareDialog({
                    id: folder.id,
                    shortcut_document_id: folder.shortcut_document_id,
                });
            }
        },
    };
}

/**
 * Hook to setup the file previewer
 */
function useDocumentsViewFilePreviewer({
    getSelectedDocumentsElements,
    setPreviewStore,
    isRecordPreviewable = () => true,
}) {
    const component = useComponent();
    const env = useEnv();
    const bus = env.documentsView.bus;
    /** @type {import("@documents/core/document_service").DocumentService} */
    const documentService = useService("document.document");
    /** @type {import("@mail/core/common/store_service").Store} */
    const store = useService("mail.store");

    const onOpenDocumentsPreview = async ({
        documents,
        mainDocument,
        isPdfSplit,
        embeddedActions,
        hasPdfSplit,
    }) => {
        const openPdfSplitter = (documents) => {
            let newDocumentIds = [];
            let forceDelete = false;
            component.dialogService.add(
                PdfManager,
                {
                    documents: documents.map((doc) => doc.data),
                    embeddedActions,
                    onProcessDocuments: async ({
                        documentIds,
                        actionId,
                        exit,
                        isForcingDelete,
                    }) => {
                        forceDelete = isForcingDelete;
                        if (documentIds && documentIds.length) {
                            newDocumentIds = [...new Set(newDocumentIds.concat(documentIds))];
                        }
                        if (actionId) {
                            await component.embeddedAction(documentIds, actionId, !exit);
                        }
                    },
                },
                {
                    onClose: async () => {
                        if (!newDocumentIds.length && !forceDelete) {
                            return;
                        }
                        await component.model.load();
                        for (const record of documents) {
                            if (!newDocumentIds.includes(record.resId)) {
                                await record.model.root.deleteRecords(record);
                            }
                        }
                        let count = 0;
                        for (const record of env.model.root.records.filter((r) =>
                            newDocumentIds.includes(r.resId),
                        )) {
                            record.onRecordClick(null, {
                                isKeepSelection: count++ !== 0,
                                isRangeSelection: false,
                            });
                        }
                    },
                }
            );
        };
        if (isPdfSplit) {
            openPdfSplitter(documents);
            return;
        }
        const documentsRecords = (
            (documents.length === 1 && component.model.root.records) ||
            documents
        )
            .filter((rec) => isRecordPreviewable(rec) && rec.isViewable())
            .map((rec) => {
                const getRecordAttachment = (rec) => {
                    rec = rec.shortcutTarget;
                    return {
                        // A negative ID prevents a reload from resolving to a real record, ensuring that the document name
                        // is always shown instead of the potentially non renamed attachment name.
                        id: -rec.resId,
                        name: rec.data.name,
                        mimetype: rec.data.mimetype,
                        url: rec.data.url,
                        documentId: rec.resId,
                        documentData: rec.data,
                    };
                };
                return store.Document.insert({
                    id: rec.resId,
                    attachment: getRecordAttachment(rec),
                    name: rec.data.name,
                    mimetype: rec.data.mimetype,
                    url: rec.data.url,
                    displayName: rec.data.display_name,
                    record: rec,
                });
            });
        // If there is a scrollbar we don't want it whenever the previewer is opened
        if (component.root.el) {
            component.root.el.querySelector(".o_documents_view").classList.add("overflow-hidden");
        }
        const selectedDocument = documentsRecords.find(
            (rec) => rec.id === (mainDocument || documents[0]).resId
        );
        documentService.documentList = {
            documents: documentsRecords || [],
            initialRecordSelectionLength: documents.length,
            pdfManagerOpenCallback: (documents) => {
                openPdfSplitter(documents);
            },
            onDeleteCallback: () => {
                // We want to focus on the first selected document's element
                const elements = getSelectedDocumentsElements();
                if (elements.length) {
                    elements[0].focus();
                }
                if (component.root?.el) {
                    component.root.el
                        .querySelector(".o_documents_view")
                        .classList.remove("overflow-hidden");
                }

                setPreviewStore({});
            },
            hasPdfSplit,
            selectedDocument,
        };

        const previewStore = {
            documentList: documentService.documentList,
            startIndex: documentsRecords.indexOf(selectedDocument),
            attachments: documentsRecords.map((doc) => doc.attachment),
        };

        documentService.setPreviewedDocument(selectedDocument);

        setPreviewStore({ ...previewStore });
    };

    useBus(bus, "documents-open-preview", async (ev) => {
        component.onOpenDocumentsPreview(ev.detail);
    });
    useBus(bus, "documents-close-preview", () => {
        documentService.setPreviewedDocument(null);
        documentService.documentList?.onDeleteCallback();
    });

    return {
        onOpenDocumentsPreview,
    };
}

/**
 * Hook to setup file upload
 */
function useDocumentsViewFileUpload() {
    const component = useComponent();
    const env = useEnv();
    const bus = env.documentsView.bus;
    const notification = useService("notification");
    const fileUpload = useService("file_upload");
    const documentService = useService("document.document");

    const handleUploadError = (result) => {
        notification.add(result.error, {
            title: _t("Error"),
            sticky: true,
        });
    };

    let wasUsingSampleModel = false;
    useBus(fileUpload.bus, "FILE_UPLOAD_ADDED", () => {
        if (env.model.useSampleModel) {
            wasUsingSampleModel = true;
            env.model.useSampleModel = false;
        }
    });

    useBus(fileUpload.bus, "FILE_UPLOAD_ERROR", async (ev) => {
        const { upload } = ev.detail;
        if (wasUsingSampleModel) {
            wasUsingSampleModel = false;
            env.model.useSampleModel = true;
        }
        if (upload.state !== "error") {
            return;
        }
        handleUploadError({
            error: _t("An error occured while uploading."),
        });
    });

    useBus(documentService.bus, "DOCUMENT_RELOAD", async (ev) => {
        await env.searchModel._reloadSearchModel(true);
        await env.model.load();
        await env.model.notify();
    });

    useBus(fileUpload.bus, "FILE_UPLOAD_LOADED", async (ev) => {
        wasUsingSampleModel = false;
        const { upload } = ev.detail;
        const xhr = upload.xhr;
        if (xhr.status !== 200) {
            handleUploadError({
                error: _t("status code: %(status)s, message: %(message)s", {
                    status: xhr.status,
                    message: xhr.response,
                })
            });
            return
        }
        // Depending on the controller called, the response is different:
        // /documents/upload/xx: returns an array of document ids
        // /mail/attachment/upload: returns an object { "ir.attachment": ... }
        const response = JSON.parse(xhr.response);
        const newDocumentIds = Array.isArray(response) ? response : undefined;
        env.model.useSampleModel = false;
        await env.model.load(component.props);
        if (!newDocumentIds) {
            return;
        }
        const records = env.model.root.records;
        let count = 0;
        for (const record of records) {
            if (!newDocumentIds.includes(record.resId)) {
                continue;
            }
            record.onRecordClick(null, {
                isKeepSelection: count++ !== 0,
                isRangeSelection: false,
            });
        }
    });

    /**
     * Create several new documents inside a given folder (folder accessToken) or replace
     * the document's attachment by the given single file (binary accessToken).
     */
    const uploadFiles = async ({ files, accessToken, context }) => {
        if (env.searchModel.getSelectedFolderId() === "COMPANY") {
            // to upload in the COMPANY folder, we need to set Odoobot as owner
            context.default_owner_id = documentService.store.odoobot.userId;
        } else if (!accessToken && context.documents_unique_folder_id) {
            const folder = env.searchModel.getFolderById(context.documents_unique_folder_id);
            if (folder) {
                accessToken = folder.access_token;
            }
        }
        await documentService.uploadDocument(files, accessToken, context);
    };

    useBus(bus, "documents-upload-files", (ev) => {
        component.uploadFiles({
            ...ev.detail,
            context: {
                ...component.props.context,
                ...ev.detail.context,
            },
        });
    });

    return {
        uploadFiles,
        onFileInputChange: async (ev) => {
            if (!ev.target.files.length) {
                return;
            }
            await component.uploadFiles({
                files: ev.target.files,
                accessToken: documentService.currentFolderAccessToken,
                context: component.props.context,
            });
            ev.target.value = "";
        },
    };
}

/**
 * Trigger embedded action hook.
 * NOTE: depends on env.model being set
 */
export function useEmbeddedAction() {
    const env = useEnv();
    const orm = useService("orm");
    const notification = useService("notification");
    const action = useService("action");
    return {
        embeddedAction: async (documentIds, actionId, preventReload = false) => {
            const context = {
                active_model: "documents.document",
                active_ids: documentIds,
            };
            const result = await orm.call(
                "documents.document",
                "action_execute_embedded_action",
                [actionId],
                {
                    context,
                }
            );

            if (result && typeof result === "object") {
                if (Object.prototype.hasOwnProperty.call(result, "warning")) {
                    notification.add(
                        markup(
                            `<ul>${result["warning"]["documents"]
                                .map((d) => `<li>${escape(d)}</li>`)
                                .join("")}</ul>`
                        ),
                        {
                            title: result["warning"]["title"],
                            type: "danger",
                        }
                    );
                    if (!preventReload) {
                        await env.model.load();
                    }
                } else if (!preventReload) {
                    await action.doAction(result, {
                        onClose: async () => await env.model.load(),
                    });
                    return;
                }
            } else if (!preventReload) {
                await env.model.load();
            }
        },
    };
}
