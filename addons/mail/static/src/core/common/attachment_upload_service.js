import { EventBus } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class AttachmentUploadService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        this.fileUploadService = services["file_upload"];
        /** @type {import("@mail/core/common/store_plugin").Store} */
        this.store = services["mail.store"];
        this.notificationService = services["notification"];

        this.nextId = -1;
        this.abortByAttachmentId = new Map();
        /** @type {Map<number, (value?: void) => void} */
        this.resolveUploadByAttachmentId = new Map();
        /** @type {Map<number, Promise<import("models").Attachment|undefined>>} */
        this.uploadPromiseByAttachmentId = new Map();
        /** Number of messages whose post waits for their attachments to be uploaded. */
        this.pendingPostCount = 0;
        this.unsubscribeBeforeUnload = undefined;
        this.deletingAttachmentIds = new Set();
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
                upload.xhr.upload.addEventListener("progress", (ev) =>
                    this._onUploadProgress(tmpId, ev)
                );
                const attachment = this.store["ir.attachment"].insert(
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
                const resolveUpload = this.resolveUploadByAttachmentId.get(tmpId);
                if (upload.xhr.status === 413) {
                    this.notificationService.add(_t("File too large"), { type: "danger" });
                    resolveUpload();
                    this._cleanupUploading(tmpId);
                    return;
                }
                if (upload.xhr.status !== 200) {
                    this.notificationService.add(_t("Server error"), { type: "danger" });
                    resolveUpload();
                    this._cleanupUploading(tmpId);
                    return;
                }
                const response = JSON.parse(upload.xhr.response);
                if (response.error) {
                    this.notificationService.add(response.error, { type: "danger" });
                    resolveUpload();
                    this._cleanupUploading(tmpId);
                    return;
                }
                const { thread, composer } = this.targetsByTmpId.get(tmpId);
                this._processLoaded(thread, composer, response, tmpId, resolveUpload);
            }
        );
        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_ERROR",
            ({ detail: { upload } }) => {
                const tmpId = parseInt(upload.data.get("temporary_id"));
                if (!this.uploadingAttachmentIds.has(tmpId)) {
                    return;
                }
                const resolveUpload = this.resolveUploadByAttachmentId.get(tmpId);
                resolveUpload();
                this._cleanupUploading(tmpId);
            }
        );
    }

    _processLoaded(thread, composer, { data }, tmpId, resolveUpload) {
        const { store_data, attachment_id } = data;
        this.store.insert(store_data);
        /** @type {import("models").Attachment} */
        const attachment = this.store["ir.attachment"].get(attachment_id);
        const pendingMessage = this.store["ir.attachment"].get(tmpId)?.message;
        if (pendingMessage) {
            // The composer was cleared when the message was sent while the
            // file was uploading: the attachment belongs to that message now.
            const index = pendingMessage.attachment_ids.findIndex(({ id }) => id === tmpId);
            pendingMessage.attachment_ids.splice(index, 1, attachment);
        } else if (composer) {
            const index = composer.attachments.findIndex(({ id }) => id === tmpId);
            if (index >= 0) {
                composer.attachments[index] = attachment;
            } else {
                composer.attachments.push(attachment);
            }
        }
        resolveUpload(attachment);
        this._fileUploadBus.trigger("UPLOAD", thread);
        this._cleanupUploading(tmpId);
    }

    _cleanupUploading(tmpId) {
        this.abortByAttachmentId.delete(tmpId);
        this.resolveUploadByAttachmentId.delete(tmpId);
        this.uploadPromiseByAttachmentId.delete(tmpId);
        this.uploadingAttachmentIds.delete(tmpId);
        this.targetsByTmpId.delete(tmpId);
        this.store["ir.attachment"].get(tmpId)?.delete();
    }

    /**
     * @param {number} tmpId
     * @param {ProgressEvent} ev
     */
    _onUploadProgress(tmpId, { loaded, total }) {
        const attachment = this.store["ir.attachment"].get(tmpId);
        if (attachment && total) {
            attachment.uploadProgress = Math.min(loaded / total, 1);
        }
    }

    /**
     * Wait for the given attachments to be uploaded, while warning the user
     * that leaving the page would lose the message waiting for them. Must be
     * called as soon as the message is sent, before the uploads complete: they
     * are detached from their composer, which is cleared, and their promises
     * are removed once completed.
     *
     * @param {import("models").Attachment[]} attachments
     * @returns {Promise<import("models").Attachment[]>} the uploaded attachments,
     *  in the same order, without the ones whose upload failed or was cancelled.
     */
    async waitForUploads(attachments) {
        const uploadPromises = attachments.map((attachment) => {
            if (!attachment.uploading) {
                return attachment;
            }
            const { thread } = this.targetsByTmpId.get(attachment.id);
            this.targetsByTmpId.set(attachment.id, { thread });
            return this.uploadPromiseByAttachmentId.get(attachment.id);
        });
        this.pendingPostCount++;
        if (this.pendingPostCount === 1) {
            // Only listen while needed, as Firefox does not place pages with
            // beforeunload listeners in the bfcache.
            const onBeforeUnload = (ev) => ev.preventDefault();
            window.addEventListener("beforeunload", onBeforeUnload);
            this.unsubscribeBeforeUnload = () =>
                window.removeEventListener("beforeunload", onBeforeUnload);
        }
        try {
            const uploaded = await Promise.all(uploadPromises);
            return uploaded.filter(Boolean);
        } finally {
            this.pendingPostCount--;
            if (this.pendingPostCount === 0) {
                this.unsubscribeBeforeUnload();
                this.unsubscribeBeforeUnload = undefined;
            }
        }
    }

    getUploadURL(thread) {
        return "/mail/attachment/upload";
    }

    /**
     * Cancel multiple uploads given a list of attachment records.
     * @param {import("models").Attachment[]} attachments
     */
    cancelUploads(attachments) {
        for (const att of attachments) {
            const tmpId = att.id;
            const resolveUpload = this.resolveUploadByAttachmentId.get(tmpId);
            const abort = this.abortByAttachmentId.get(tmpId);
            this._cleanupUploading(tmpId);
            resolveUpload();
            abort();
        }
    }

    /**
     * Remove the given attachments, cancelling the uploads in progress and
     * deleting the others on the server, all at once.
     * @param {import("models").Attachment[]} attachments
     * @param {Object} [options] see `removeAttachments`
     */
    async unlink(attachments, options) {
        const attachmentsToUnlink = attachments.filter((attachment) => {
            if (this.deletingAttachmentIds.has(attachment.id)) {
                return false;
            }
            this.deletingAttachmentIds.add(attachment.id);
            return true;
        });

        try {
            await this.store.removeAttachments(attachmentsToUnlink, options);
        } finally {
            for (const attachment of attachmentsToUnlink) {
                this.deletingAttachmentIds.delete(attachment.id);
            }
        }
    }

    async upload(thread, composer, file, options) {
        const tmpId = this.nextId--;
        const tmpURL = URL.createObjectURL(file);
        return this._upload(thread, composer, file, options, tmpId, tmpURL);
    }

    async _upload(thread, composer, file, options, tmpId, tmpURL) {
        this.targetsByTmpId.set(tmpId, { composer, thread });
        this.uploadingAttachmentIds.add(tmpId);
        const { promise: uploadPromise, resolve: resolveUpload } = Promise.withResolvers();
        this.resolveUploadByAttachmentId.set(tmpId, resolveUpload);
        this.uploadPromiseByAttachmentId.set(tmpId, uploadPromise);
        await this.fileUploadService
            .upload(this.getUploadURL(thread), [file], {
                buildFormData: (formData) => {
                    this._buildFormData(formData, tmpURL, thread, composer, tmpId, options);
                },
            })
            .catch((e) => {
                if (e.name !== "AbortError") {
                    throw e;
                }
            });
        return uploadPromise;
    }

    /**
     * @param {import("@odoo/owl").Signal<import("models").Thread>} thread
     * @param {(thread: import("models").Thread) => void} onFileUploaded
     */
    onFileUploaded(thread, onFileUploaded) {
        this._fileUploadBus.addEventListener("UPLOAD", ({ detail }) => {
            if (thread()?.eq(detail)) {
                onFileUploaded(detail);
            }
        });
    }

    _buildFormData(formData, tmpURL, thread, composer, tmpId, options) {
        formData.append("thread_id", thread.id);
        formData.append("tmp_url", tmpURL);
        formData.append("thread_model", thread.model);
        formData.append("is_pending", Boolean(composer));
        formData.append("temporary_id", tmpId);
        if (options?.activity) {
            formData.append("activity_id", options.activity.id);
        }
        return formData;
    }

    _makeAttachmentData(upload, tmpId, thread, tmpUrl) {
        const attachmentData = {
            id: tmpId,
            mimetype: upload.type,
            name: upload.title,
            thread,
            extension: upload.title.split(".").pop(),
            file_size: upload.data.get("ufile")?.size,
            uploadProgress: 0,
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
