import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";

let nextId = -1;

export class AttachmentUploadService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        this.fileUploadService = services["file_upload"];
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        this.notificationService = services["notification"];

        this.abortByAttachmentId = new Map();
        this.deferredByAttachmentId = new Map();
        this.uploadingAttachmentIds = new Set();
        this.hookersByTmpId = new Map();

        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_ADDED",
            ({ detail: { upload } }) => {
                const tmpId = parseInt(upload.data.get("temporary_id"));
                if (!this.uploadingAttachmentIds.has(tmpId)) {
                    return;
                }
                const hooker = this.hookersByTmpId.get(tmpId);
                const threadId = parseInt(upload.data.get("thread_id"));
                const threadModel = upload.data.get("thread_model");
                const tmpUrl = upload.data.get("tmp_url");
                const thread = this.store.Thread.insert({
                    model: threadModel,
                    id: threadId,
                });
                this.abortByAttachmentId.set(tmpId, upload.xhr.abort.bind(upload.xhr));
                const attachment = this.store.Attachment.insert(
                    this._makeAttachmentData(
                        upload,
                        tmpId,
                        hooker.composer ? undefined : thread,
                        tmpUrl
                    )
                );
                if (hooker.composer) {
                    hooker.composer.attachments.push(attachment);
                }
            }
        );
        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_LOADED",
            ({ detail: { upload } }) => {
                const tmpId = parseInt(upload.data.get("temporary_id"));
                if (!this.uploadingAttachmentIds.has(tmpId)) {
                    return;
                }
                this.uploadingAttachmentIds.delete(tmpId);
                this.abortByAttachmentId.delete(tmpId);
                const hooker = this.hookersByTmpId.get(tmpId);
                if (upload.xhr.status === 413) {
                    this.notificationService.add(_t("File too large"), { type: "danger" });
                    this.hookersByTmpId.delete(tmpId);
                    return;
                }
                if (upload.xhr.status !== 200) {
                    this.notificationService.add(_t("Server error"), { type: "danger" });
                    this.hookersByTmpId.delete(tmpId);
                    return;
                }
                const response = JSON.parse(upload.xhr.response);
                if (response.error) {
                    this.notificationService.add(response.error, { type: "danger" });
                    this.hookersByTmpId.delete(tmpId);
                    return;
                }
                const threadId = parseInt(upload.data.get("thread_id"));
                const threadModel = upload.data.get("thread_model");
                const thread = this.store.Thread.get({ model: threadModel, id: threadId });
                const attachment = this.store.Attachment.insert({
                    ...(response?.result ?? response), // FIXME: this should be only response. HOOT tests returns wrong data {result, error}
                    extension: upload.title.split(".").pop(),
                    thread: hooker.composer ? undefined : thread,
                });
                if (hooker.composer) {
                    const index = hooker.composer.attachments.findIndex(({ id }) => id === tmpId);
                    if (index >= 0) {
                        hooker.composer.attachments[index] = attachment;
                    } else {
                        hooker.composer.attachments.push(attachment);
                    }
                }
                const def = this.deferredByAttachmentId.get(tmpId);
                const tmpAttachment = this.store.Attachment.get(tmpId);
                if (tmpAttachment) {
                    this.unlink(tmpAttachment);
                }
                if (def) {
                    def.resolve(attachment);
                    this.deferredByAttachmentId.delete(tmpId);
                }
                hooker.onFileUploaded?.();
                this.hookersByTmpId.delete(tmpId);
            }
        );
        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_ERROR",
            ({ detail: { upload } }) => {
                const tmpId = parseInt(upload.data.get("temporary_id"));
                if (!this.uploadingAttachmentIds.has(tmpId)) {
                    return;
                }
                this.abortByAttachmentId.delete(tmpId);
                this.deferredByAttachmentId.delete(tmpId);
                this.uploadingAttachmentIds.delete(parseInt(tmpId));
                this.hookersByTmpId.delete(tmpId);
            }
        );
    }

    get uploadURL() {
        return "/mail/attachment/upload";
    }

    async unlink(attachment) {
        const abort = this.abortByAttachmentId.get(attachment.id);
        const def = this.deferredByAttachmentId.get(attachment.id);
        if (abort) {
            abort();
            def.resolve();
        }
        this.abortByAttachmentId.delete(attachment.id);
        this.deferredByAttachmentId.delete(attachment.id);
        await attachment.remove();
    }

    async uploadFile(hooker, file, options) {
        const tmpId = nextId--;
        this.hookersByTmpId.set(tmpId, hooker);
        this.uploadingAttachmentIds.add(tmpId);
        await this.fileUploadService
            .upload(this.uploadURL, [file], {
                buildFormData: (formData) => {
                    this._makeFormData(formData, file, hooker, tmpId, options);
                },
            })
            .catch((e) => {
                if (e.name !== "AbortError") {
                    throw e;
                }
            });
        const uploadDoneDeferred = new Deferred();
        this.deferredByAttachmentId.set(tmpId, uploadDoneDeferred);
        return uploadDoneDeferred;
    }

    _makeFormData(formData, file, hooker, tmpId, options) {
        formData.append("thread_id", hooker.thread.id);
        formData.append("tmp_url", URL.createObjectURL(file));
        formData.append("thread_model", hooker.thread.model);
        formData.append("is_pending", Boolean(hooker.composer));
        formData.append("temporary_id", tmpId);
        return formData;
    }

    _makeAttachmentData(upload, tmpId, thread, tmpUrl) {
        const attachmentData = {
            filename: upload.title,
            id: tmpId,
            mimetype: upload.type,
            name: upload.title,
            thread,
            extension: upload.title.split(".").pop(),
            uploading: true,
            tmpUrl,
        };
        return attachmentData;
    }
}

export const attachmentUploadService = {
    dependencies: ["file_upload", "mail.store", "notification"],
    start(env, services) {
        return new AttachmentUploadService(env, services);
    },
};

registry.category("services").add("mail.attachment_upload", attachmentUploadService);
