/** @odoo-module **/

import { debounce } from '@bus/workers/websocket_worker_utils';
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { KeepLast } from "@web/core/utils/concurrency";
import { intersection } from "@web/core/utils/arrays";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { x2ManyCommands } from "@web/core/orm_service";
import { browser } from "@web/core/browser/browser";
import { useBus, useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FileUploader } from "@web/views/fields/file_handler";
import { Chatter } from "@mail/core/web/chatter";
import { DocumentsInspectorField } from "./documents_inspector_field";
import { download } from "@web/core/network/download";
import { onNewPdfThumbnail } from "../helper/documents_pdf_thumbnail_service";
import dUtils from "@documents/views/helper/documents_utils";
import { useTriggerRule, toggleArchive } from "@documents/views/hooks";
import { deserializeDateTime, serializeDate } from "@web/core/l10n/dates";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import {
    Component,
    markup,
    useEffect,
    useState,
    useRef,
    onPatched,
    onWillUpdateProps,
    onWillStart,
} from "@odoo/owl";

const { DateTime } = luxon;

export const inspectorFields = [
    "attachment_id",
    "active",
    "activity_ids",
    "available_rule_ids",
    "checksum",
    "display_name",
    "file_extension",
    "folder_id",
    "thumbnail_status",
    "lock_uid",
    "message_attachment_count",
    "message_follower_ids",
    "message_ids",
    "mimetype",
    "name",
    "owner_id",
    "partner_id",
    "previous_attachment_ids",
    "res_id",
    "res_model",
    "res_model_name",
    "res_name",
    "tag_ids",
    "type",
    "url",
    "url_preview_image",
    "file_size",
];

export class DocumentsInspector extends Component {
    static props = [
        "archInfo", // Archinfo of the view
        "count", // Current number of records displayed in the view
        "fileSize", // Total size of (in MB) of records displayed in the view
        "documents", // Array of records
        "fields",
    ];

    static components = {
        AutoComplete,
        Chatter,
        DocumentsInspectorField,
        FileUploader,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.documentsReplaceInput = useRef("replaceFileInput");
        this.chatterContainer = useRef("chatterContainer");
        this.keepLast = new KeepLast();
        this.previewLockCount = 0;
        this.deserializeDateTime = deserializeDateTime;
        const { triggerRule } = useTriggerRule();
        this._triggerRule = triggerRule;
        const { bus: fileUploadBus } = useService("file_upload");
        useBus(fileUploadBus, "FILE_UPLOAD_LOADED", (ev) => {
            const documentId = ev.detail.upload.data.get("document_id");
            if (documentId && this.resIds.includes(Number.parseInt(documentId))) {
                this.state.previousAttachmentDirty = true;
            }
        });

        // Avoid generating new urls if they were generated within this component's lifetime
        this.generatedUrls = {};
        this.state = useState({
            previousAttachmentData: null,
            previousAttachmentDirty: true,
            showChatter: this.isMobile,
        });
        const updateLockedState = (props) => {
            this.isLocked =
                (props.documents.find(
                    (rec) => rec.data.lock_uid && rec.data.lock_uid[0] !== session.uid
                ) &&
                    true) ||
                false;
            const folderIds = props.documents.map((rec) => rec.data.folder_id[0]);
            const folders = this.env.searchModel
                .getFolders()
                .filter((folder) => folderIds.includes(folder.id));
            this.isEditDisabled = !!folders.find((folder) => !folder.has_write_access);
        };
        onWillStart(() => {
            updateLockedState(this.props);
            this.updateAttachmentHistory(null);
        });
        onWillUpdateProps((nextProps) => {
            this.generatedUrl = false;
            updateLockedState(nextProps);
            this.updateAttachmentHistory(nextProps);
        });

        const chatterReloadHandler = async () => {
            const record = this.props.documents[0];
            if (!record) {
                return;
            }
            await record.load();
        };
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                el.addEventListener("reload", chatterReloadHandler);
                return () => {
                    el.removeEventListener("reload", chatterReloadHandler);
                };
            },
            () => [
                this.chatterContainer.el &&
                    this.chatterContainer.el.querySelector(".o-mail-Chatter"),
            ]
        );
        this.onRestorePreviousAttachment = debounce(this.onRestorePreviousAttachment, 300, true);

        // Pdf thumbnails
        this.pdfService = useService("documents_pdf_thumbnail");
        onWillStart(() => {
            this.pdfService.enqueueRecords(this.props.documents);
        });
        onWillUpdateProps((nextProps) => {
            this.pdfService.enqueueRecords(nextProps.documents);
        });
        onNewPdfThumbnail(({ detail }) => {
            if (this.props.documents.find((rec) => rec.resId === detail.record.resId)) {
                this.render(true);
            }
        });

        //Mobile specific
        if (!this.env.isSmall) {
            return;
        }
        this.inspectorMobileRef = useRef("inspectorMobile");
        this.shouldOpenInspector = false;
        onWillUpdateProps((nextProps) => {
            // Only open the inspector if there is only one selected element and
            //  it was not previously selected.
            this.shouldOpenInspector = nextProps.documents.length === 1;
        });
        onPatched(() => {
            if (!this.inspectorMobileRef.el) {
                return;
            }
            if (this.shouldOpenInspector) {
                this.inspectorMobileRef.el.setAttribute("open", "");
            }
        });
    }

    get resIds() {
        return this.props.documents.map((rec) => rec.resId);
    }

    get isDebugMode() {
        return Boolean(odoo.debug);
    }

    get isMobile() {
        return this.env.isSmall;
    }

    updateAttachmentHistory(nextProps) {
        const props = nextProps || this.props;
        const record = props.documents[0];
        if (props.documents.length !== 1) {
            this.state.showChatter = this.isMobile;
        }
        if (!record || props.documents.length !== 1 || !record.data.previous_attachment_ids.count) {
            this.keepLast.add(Promise.resolve());
            this.state.previousAttachmentData = null;
            return;
        }
        const previousRecord = this.props.documents.length === 1 && this.props.documents[0];
        if (
            nextProps &&
            previousRecord &&
            previousRecord.resId === record.resId &&
            !this.state.previousAttachmentDirty
        ) {
            return;
        }
        this.keepLast.add(
            this.orm
                .searchRead(
                    "ir.attachment",
                    [
                        [
                            "id",
                            "in",
                            record.data.previous_attachment_ids.records.map((rec) => rec.resId),
                        ],
                    ],
                    ["name", "create_date", "create_uid"],
                    {
                        order: "create_date desc",
                    }
                )
                .then((result) => {
                    this.state.previousAttachmentData = result;
                    this.state.previousAttachmentDirty = false;
                })
        );
    }

    async _reloadSearchModel() {
        await this.env.searchModel._fetchSections(
            this.env.searchModel.getSections(
                (s) => s.type === "category" && s.fieldName === "folder_id"
            ),
            []
        );
        await this.env.searchModel._notify();
    }

    getCurrentFolder() {
        return this.env.searchModel.getSelectedFolder();
    }

    getFolderDescription() {
        return markup(this.getCurrentFolder().description);
    }

    /**
     * Returns an object with additional data for our record
     */
    getRecordAdditionalData(record) {
        const additionalData = {
            isGif: new RegExp("image.*(gif)").test(record.data.mimetype),
            isImage: new RegExp("image.*(jpeg|jpg|png|webp)").test(record.data.mimetype),
            isYoutubeVideo: false,
            youtubeToken: undefined,
            url_preview_image: record.data.url_preview_image,
        };
        if (record.data.url && record.data.url.length) {
            const youtubeUrlMatch = record.data.url.match(
                "youtu(?:.be|be.com)/(?:.*v(?:/|=)|(?:.*/)?)([a-zA-Z0-9-_]{11})"
            );
            if (youtubeUrlMatch && youtubeUrlMatch.length > 1) {
                additionalData.isYoutubeVideo = true;
                additionalData.youtubeToken = youtubeUrlMatch[1];
            }
        }
        return additionalData;
    }

    /**
     * Returns the classes to give to the file preview
     */
    getPreviewClasses(record, additionalData) {
        const nbPreviews = this.props.documents.length;
        const classes = ["o_document_preview"];
        if (record.data.type === "empty") {
            classes.push("o_document_request_preview");
        }
        if (nbPreviews === 1) {
            classes.push("o_documents_single_preview");
        }
        if (
            additionalData.isImage ||
            additionalData.isYoutubeVideo ||
            record.data.url_preview_image ||
            (record.isPdf() && record.hasThumbnail())
        ) {
            classes.push("o_documents_preview_image");
        } else {
            classes.push("o_documents_preview_mimetype");
        }
        if (additionalData.isYoutubeVideo || additionalData.isGif) {
            classes.push("o_non_image_preview");
        }
        return classes.join(" ");
    }

    isPdfOnly() {
        return this.props.documents.every((record) => record.isPdf());
    }

    download(records) {
        if (records.length === 1) {
            download({
                data: {},
                url: `/documents/content/${records[0].resId}`,
            });
        } else {
            download({
                data: {
                    file_ids: records.map((rec) => rec.resId),
                    zip_name: `documents-${serializeDate(DateTime.now())}.zip`,
                },
                url: "/document/zip",
            });
        }
    }

    onDownload() {
        const documents = this.props.documents.filter((rec) => rec.data.type !== "empty");
        if (!documents.length) {
            return;
        }
        const linkDocuments = documents.filter((el) => el.data.type === "url");
        const noLinkDocuments = documents.filter((el) => el.data.type !== "url");
        // Manage link documents
        if (documents.length === 1 && linkDocuments.length) {
            // Redirect to the link
            let url = linkDocuments[0].data.url;
            url = /^(https?|ftp):\/\//.test(url) ? url : "http://" + url;
            window.open(url, "_blank");
        } else if (noLinkDocuments.length) {
            // Download all documents which are not links
            this.download(noLinkDocuments);
        }
    }

    async onShare() {
        const resIds = this.props.documents
            .filter((rec) => rec._values.type !== "empty")
            .map((rec) => rec._values.id);
        const linkProportion = await dUtils.get_link_proportion(this.orm, resIds ? resIds : false);
        if (!this.generatedUrls[resIds]) {
            const vals = await this.createShareVals();
            this.generatedUrls[resIds] = await this.orm.call(
                "documents.share",
                "action_get_share_url",
                [vals]
            );
        }
        setTimeout(async () => {
            await browser.navigator.clipboard.writeText(this.generatedUrls[resIds]);
            if (linkProportion == "some") {
                this.notificationService.add(
                    _t("The share url has been copied to your clipboard. Links were excluded."),
                    { type: "warning" }
                );
            } else {
                this.notificationService.add(_t("The share url has been copied to your clipboard."), {
                    type: "success",
                });
            }
        });
    }

    async createShareVals() {
        const resIds = this.props.documents
            .filter((rec) => rec._values.type !== "empty")
            .map((rec) => rec.resId);
        return {
            document_ids: [x2ManyCommands.set(resIds)],
            folder_id: this.env.searchModel.getSelectedFolderId(),
            type: "ids",
        };
    }

    async onReplace(ev) {
        if (!ev.target.files.length) {
            return;
        }
        const index = Number(ev.target.getAttribute("data-index"));
        const record = this.props.documents[index];

        await this.env.documentsView.bus.trigger("documents-upload-files", {
            files: ev.target.files,
            folderId:
                this.env.searchModel.getSelectedFolderId() ||
                (record.data.folder_id && record.data.folder_id[0]),
            recordId: record.resId,
            tagIds: this.env.searchModel.getSelectedTagIds(),
        });
        ev.target.value = "";
    }

    async onLock() {
        await this.doLockAction(async () => {
            const record = this.props.documents[0];
            await this.orm.call("documents.document", "toggle_lock", this.resIds);
            await record.load();
        });
    }

    async onArchive() {
        const record = this.props.documents[0];
        const callback = async () => {
            await toggleArchive(record.model, record.resModel, this.resIds, true);
        };
        record.openDeleteConfirmationDialog(record.model.root, callback, false);
    }

    async onUnarchive() {
        const record = this.props.documents[0];
        await toggleArchive(record.model, record.resModel, this.resIds, false);
        this.env.documentsView.bus.trigger("documents-close-preview");
        await this._reloadSearchModel();
    }

    onDelete() {
        const records = this.props.documents;
        const callback = async () => {
            const model = records[0].model;
            await model.root.deleteRecords(records);
            await model.load(this.env.model.config);
            await model.notify();
        };
        records[0].openDeleteConfirmationDialog(records[0].model.root, callback, true);
    }

    getFieldProps(fieldName, additionalProps) {
        // `documents` might come from a state, and can be a Proxy object at this point
        // and make an infinite loop (the record is given to `Field`, which will change
        // some attributes (see @evalContext), and so trigger the update of the state
        // 2 components above, that will re-instantiate the component `Field` and then
        // re-modify the attributes, etc) so we convert it back to the target
        // of the proxy object. Ideally, objects should be unproxyfied when we pass them
        // by props (to avoid that type of loop).
        const rec = this.props.documents[0];
        const record = Object.create(rec.constructor.prototype);
        Object.assign(record, rec);

        const props = {
            record: record,
            name: fieldName,
            documents: [...this.props.documents],
            inspectorReadonly: this.isLocked || this.isEditDisabled,
            lockAction: this.doLockAction.bind(this),
        };
        if (additionalProps) {
            Object.assign(props, additionalProps);
        }
        return props;
    }

    _getCommonM2M(field) {
        const documents = this.props.documents;
        let commonData = documents[0].data[field].records.map((rec) => rec.resId);
        for (let idx = 1; idx < documents.length; idx++) {
            if (commonData.length === 0) {
                break;
            }
            commonData = intersection(
                commonData,
                documents[idx].data[field].records.map((rec) => rec.resId)
            );
        }
        return commonData.map((id) =>
            documents[0].data[field].records.find((data) => data.resId === id)
        );
    }

    getCommonTags() {
        const searchModelTags = this.env.searchModel.getTags().reduce((res, tag) => {
            res[tag.id] = tag;
            return res;
        }, {});
        return this._getCommonM2M("tag_ids")
            .filter((rec) => searchModelTags[rec.resId])
            .map((rec) => {
                const tag = searchModelTags[rec.resId];
                return {
                    id: rec.resId,
                    name: tag.display_name,
                    group_name: tag.group_name,
                };
            });
    }

    getCommonRules() {
        let commonRules = this._getCommonM2M("available_rule_ids");
        if (this.props.documents.length > 1) {
            commonRules = commonRules.filter((rule) => !rule.data.limited_to_single_record);
        }
        return commonRules;
    }

    getAdditionalTags(commonTags) {
        return this.env.searchModel.getTags().filter((tag) => {
            return !commonTags.find((cTag) => cTag.id === tag.id);
        });
    }

    async removeTag(tag) {
        const resIds = this.props.documents.map((r) => r.resId);
        await this.env.searchModel.updateRecordTagId(resIds, tag.id, 3);
    }

    async addTag(tag, { input }) {
        const resIds = this.props.documents.map((r) => r.resId);
        await this.env.searchModel.updateRecordTagId(resIds, tag.value);

        input.focus();
    }

    getTagAutocompleteProps(additionalTags) {
        return {
            value: "",
            onSelect: this.addTag.bind(this),
            sources: [
                {
                    options: (request) => {
                        request = request.toLowerCase();
                        return additionalTags
                            .filter((tag) =>
                                (tag.group_name + " > " + tag.display_name)
                                    .toLowerCase()
                                    .includes(request)
                            )
                            .map((tag) => {
                                return {
                                    id: tag.id,
                                    value: tag.id,
                                    label: tag.group_name + " > " + tag.display_name,
                                };
                            });
                    },
                },
            ],
            placeholder: _t(" + Add a tag"),
        };
    }

    async onClickResModel() {
        const record = this.props.documents[0];
        const action = await this.orm.call(
            record.data.res_model,
            "get_formview_action",
            [[record.data.res_id]],
            {
                context: record.model.user.context,
            }
        );
        await this.action.doAction(action);
    }

    async triggerRule(rule) {
        await this._triggerRule(
            this.props.documents.map((rec) => rec.resId),
            rule.resId
        );
    }

    async onDeletePreviousAttachment(attachmentId) {
        if (this.deleting) {
            return;
        }
        await this.doLockAction(async () => {
            this.deleting = true;
            await this.orm.unlink("ir.attachment", [attachmentId]);
            const record = this.props.documents[0];
            const model = this.props.documents[0].model;
            await record.load();
            this.state.previousAttachmentDirty = true;
            await model.notify();
            this.deleting = false;
        });
    }

    async onDownloadPreviousAttachment(attachmentId) {
        window.location = `/web/content/${attachmentId}?download=true`;
    }

    async onRestorePreviousAttachment(attachmentId) {
        const record = this.props.documents[0];
        await this.doLockAction(async () => {
            await this.orm.write("documents.document", [record.resId], {
                attachment_id: attachmentId,
            });
            await record.model.load();
            this.state.previousAttachmentDirty = true;
        });
    }

    openPreview(mainDocument = false, isPdfSplit = false) {
        if ((isPdfSplit && !this.isPdfOnly()) || this.previewLockCount) {
            return;
        }
        const documents = this.props.documents.filter((rec) => rec.isViewable());
        if (!documents.length) {
            return;
        }
        this.env.documentsView.bus.trigger("documents-open-preview", {
            documents: documents,
            mainDocument: mainDocument || documents[0],
            isPdfSplit,
            rules: this.getCommonRules(),
            hasPdfSplit: !this.isLocked && !this.isEditDisabled,
        });
    }

    async onEditModel() {
        const record = this.props.documents[0];
        let defaultResourceRef = false;
        if (record.data.res_model && record.data.res_id) {
            defaultResourceRef = `${record.data.res_model},${record.data.res_id}`;
        }
        const models = await this.orm.searchRead(
            "ir.model",
            [["model", "=", record.data.res_model]],
            ["id"],
            {
                limit: 1,
            }
        );
        this.action.doAction(
            {
                name: _t("Edit the linked record"),
                type: "ir.actions.act_window",
                res_model: "documents.link_to_record_wizard",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_document_ids: [record.resId],
                    default_resource_ref: defaultResourceRef,
                    default_is_readonly_model: true,
                    default_model_id: models[0].id,
                },
            },
            {
                onClose: async () => {
                    await record.model.load();
                },
            }
        );
    }

    onDeleteModel() {
        const recordId = this.props.documents[0].resId;
        const model = this.props.documents[0].model;
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Do you really want to unlink this record?"),
            confirm: async () => {
                await this.orm.call("documents.workflow.rule", "unlink_record", [[recordId]]);
                await model.load();
                model.notify();
            },
        });
    }

    async doLockAction(func) {
        this.previewLockCount++;
        await func();
        this.previewLockCount--;
    }
}

if (uiUtils.isSmall()) {
    DocumentsInspector.template = "documents.DocumentsInspectorMobile";
} else {
    DocumentsInspector.template = "documents.DocumentsInspector";
}
