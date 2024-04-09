import { EventBus } from "@odoo/owl";
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
        this._fileUploadBus = new EventBus();
        /** @type {Map<number, {composer: import("models").Composer, thread: import("models").Thread}>} */
        this.targetsByTmpId = new Map();
        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_ADDED",
            ({ detail: { upload } }) => {
                const tmpId = parseInt(upload.data.get("temporary_id"));
                if (!this.uploadingAttachmentIds.has(tmpId)) {
                    return;
                }
                const { thread, composer } = this.targetsByTmpId.get(tmpId);
                const tmpUrl = upload.data.get("tmp_url");
                this.abortByAttachmentId.set(tmpId, upload.xhr.abort.bind(upload.xhr));
                const attachment = this.store.Attachment.insert(
                    this._makeAttachmentData(upload, tmpId, composer ? undefined : thread, tmpUrl)
                );
                composer?.attachments.push(attachment);
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
                const { thread, composer } = this.targetsByTmpId.get(tmpId);
                if (upload.xhr.status === 413) {
                    this.notificationService.add(_t("File too large"), { type: "danger" });
                    this.targetsByTmpId.delete(tmpId);
                    return;
                }
                if (upload.xhr.status !== 200) {
                    this.notificationService.add(_t("Server error"), { type: "danger" });
                    this.targetsByTmpId.delete(tmpId);
                    return;
                }
                const response = JSON.parse(upload.xhr.response);
                if (response.error) {
                    this.notificationService.add(response.error, { type: "danger" });
                    this.targetsByTmpId.delete(tmpId);
                    return;
                }
                const attachment = this.store.Attachment.insert({
                    ...(response?.result ?? response), // FIXME: this should be only response. HOOT tests returns wrong data {result, error}
                    extension: upload.title.split(".").pop(),
                    thread: composer ? undefined : thread,
                });
                if (composer) {
                    const index = composer.attachments.findIndex(({ id }) => id === tmpId);
                    if (index >= 0) {
                        composer.attachments[index] = attachment;
                    } else {
                        composer.attachments.push(attachment);
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
                this._fileUploadBus.trigger("UPLOAD", thread);
                this.targetsByTmpId.delete(tmpId);
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
                this.targetsByTmpId.delete(tmpId);
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

    async upload(thread, composer, file, options) {
        const tmpId = nextId--;
        this.targetsByTmpId.set(tmpId, { composer, thread });
        this.uploadingAttachmentIds.add(tmpId);
        await this.fileUploadService
            .upload(this.uploadURL, [file], {
                buildFormData: (formData) => {
                    this._buildFormData(formData, file, thread, composer, tmpId, options);
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

    /**
     * @param {import("models").Thread} thread
     * @param {() => void} onFileUploaded
     */
    onFileUploaded(thread, onFileUploaded) {
        this._fileUploadBus.addEventListener("UPLOAD", ({ detail }) => {
            if (thread.eq(detail)) {
                onFileUploaded();
            }
        });
    }

    _buildFormData(formData, file, thread, composer, tmpId, options) {
        formData.append("thread_id", thread.id);
        formData.append("tmp_url", URL.createObjectURL(file));
        formData.append("thread_model", thread.model);
        formData.append("is_pending", Boolean(composer));
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
