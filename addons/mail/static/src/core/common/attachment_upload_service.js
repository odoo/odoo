import { UPLOAD_ERROR } from "@mail/core/common/attachment_model";

import { EventBus, usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef {Object} UploadOptions
 * @property {import("models").Activity} [activity]
 * @property {boolean} [detached] whether the attachment belongs to the caller
 *  rather than to a composer, so it is kept when the upload ends, even failed
 * @property {boolean} [voice]
 */

export class AttachmentUploadService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        this.fileUploadService = services["file_upload"];
        /** @type {import("@mail/core/common/store_plugin").Store} */
        this.store = services["mail.store"];
        this.notificationService = usePlugin(NotificationPlugin);

        this.nextId = -1;
        this.abortByAttachmentId = new Map();
        /** @type {Map<number, (value?: void) => void} */
        this.resolveUploadByAttachmentId = new Map();
        /** @type {Map<number, Promise<import("models").Attachment|undefined>>} */
        this.uploadPromiseByAttachmentId = new Map();
        /** @type {Map<number, File>} files of the uploading and failed attachments */
        this.fileByAttachmentId = new Map();
        this.deletingAttachmentIds = new Set();
        this.uploadingAttachmentIds = new Set();
        this._fileUploadBus = new EventBus();
        /** @type {Map<number, {composer: import("models").Composer, detached: boolean, thread: import("models").Thread}>} */
        this.targetsByTmpId = new Map();
        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_ADDED",
            ({ detail: { upload } }) => {
                const tmpId = parseInt(upload.data.get("temporary_id"));
                if (!this.uploadingAttachmentIds.has(tmpId)) {
                    return;
                }
                const { thread, composer, detached } = this.targetsByTmpId.get(tmpId);
                const tmpUrl = upload.data.get("tmp_url");
                this.abortByAttachmentId.set(tmpId, upload.xhr.abort.bind(upload.xhr));
                upload.xhr.upload.addEventListener("progress", (ev) =>
                    this._onUploadProgress(tmpId, ev)
                );
                const attachment = this.store["ir.attachment"].insert(
                    this._makeAttachmentData(
                        upload,
                        tmpId,
                        composer || detached ? undefined : thread,
                        tmpUrl
                    )
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
                    this._failUpload(tmpId, UPLOAD_ERROR.TOO_LARGE);
                    return;
                }
                if (upload.xhr.status !== 200) {
                    this.notificationService.add(_t("Server error"), { type: "danger" });
                    this._failUpload(tmpId, UPLOAD_ERROR.FAILED);
                    return;
                }
                const response = JSON.parse(upload.xhr.response);
                if (response.error) {
                    this.notificationService.add(response.error, { type: "danger" });
                    this._failUpload(tmpId, UPLOAD_ERROR.FAILED);
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
                // 413: Content Too Large
                this._failUpload(
                    tmpId,
                    upload.xhr.status === 413 ? UPLOAD_ERROR.TOO_LARGE : UPLOAD_ERROR.FAILED
                );
            }
        );
    }

    _processLoaded(thread, composer, { data }, tmpId, resolveUpload) {
        const { store_data, attachment_id } = data;
        this.store.insert(store_data);
        /** @type {import("models").Attachment} */
        const attachment = this.store["ir.attachment"].get(attachment_id);
        if (composer) {
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

    /**
     * The attachment of a detached upload is kept, for whoever detached it to
     * replace or remove it, and its file too when it failed.
     *
     * @param {number} tmpId
     * @param {Object} [options]
     * @param {boolean} [options.failed]
     */
    _cleanupUploading(tmpId, { failed = false } = {}) {
        const detached = this.targetsByTmpId.get(tmpId)?.detached;
        this.abortByAttachmentId.delete(tmpId);
        this.resolveUploadByAttachmentId.delete(tmpId);
        this.uploadPromiseByAttachmentId.delete(tmpId);
        this.uploadingAttachmentIds.delete(tmpId);
        this.targetsByTmpId.delete(tmpId);
        if (!detached || !failed) {
            this.fileByAttachmentId.delete(tmpId);
        }
        if (!detached) {
            this.store["ir.attachment"].get(tmpId)?.delete();
        }
    }

    /**
     * Stop the given upload, which failed. The attachment of a detached upload
     * is kept as failed, to maybe upload it again.
     *
     * @param {number} tmpId
     * @param {keyof typeof UPLOAD_ERROR} error
     */
    _failUpload(tmpId, error) {
        const resolveUpload = this.resolveUploadByAttachmentId.get(tmpId);
        const { detached } = this.targetsByTmpId.get(tmpId);
        this._cleanupUploading(tmpId, { failed: true });
        if (detached) {
            Object.assign(this.store["ir.attachment"].get(tmpId), {
                uploadError: error,
                uploading: false,
            });
        }
        resolveUpload();
    }

    /**
     * Detach the given uploads from their composer, keeping their attachment.
     *
     * @param {import("models").Attachment[]} attachments
     * @returns {Promise<import("models").Attachment|undefined>[]} the uploaded
     *  attachment of each one, undefined when its upload failed or was cancelled
     */
    detachUploads(attachments) {
        return attachments.map((attachment) => {
            if (!attachment.uploading) {
                return Promise.resolve(attachment);
            }
            Object.assign(this.targetsByTmpId.get(attachment.id), {
                composer: undefined,
                detached: true,
            });
            return this.uploadPromiseByAttachmentId.get(attachment.id);
        });
    }

    /**
     * Upload again the files of the given detached attachments, whose upload
     * failed.
     *
     * @param {import("models").Attachment[]} attachments
     * @param {import("models").Thread} thread
     * @returns {Promise<import("models").Attachment|undefined>[]} see `detachUploads`
     */
    retryUploads(attachments, thread) {
        return attachments.map((attachment) => {
            Object.assign(attachment, { uploadError: undefined, uploading: true });
            this._upload(
                thread,
                undefined,
                this.fileByAttachmentId.get(attachment.id),
                { detached: true, voice: attachment.voice },
                attachment.id,
                attachment.tmpUrl
            );
            return this.uploadPromiseByAttachmentId.get(attachment.id);
        });
    }

    /**
     * Forget the files of the given attachments whose upload failed, as they
     * are removed.
     *
     * @param {import("models").Attachment[]} attachments
     */
    forgetFailedUploads(attachments) {
        for (const { id } of attachments) {
            this.fileByAttachmentId.delete(id);
        }
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
            this.store["ir.attachment"].get(tmpId)?.delete();
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
        this.fileByAttachmentId.set(tmpId, file);
        return this._upload(thread, composer, file, options, tmpId, tmpURL);
    }

    /**
     * @param {import("models").Thread} thread
     * @param {import("models").Composer} [composer]
     * @param {File} file
     * @param {UploadOptions} [options]
     * @param {number} tmpId
     * @param {string} tmpURL
     */
    async _upload(thread, composer, file, options, tmpId, tmpURL) {
        this.targetsByTmpId.set(tmpId, {
            composer,
            detached: Boolean(options?.detached),
            thread,
        });
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

    /**
     * Fill the form data of the upload request. An attachment uploaded from a
     * composer, or detached, is pending, so it is not linked to the thread yet.
     *
     * @param {FormData} formData
     * @param {string} tmpURL
     * @param {import("models").Thread} thread
     * @param {import("models").Composer} [composer]
     * @param {number} tmpId
     * @param {UploadOptions} [options]
     * @returns {FormData}
     */
    _buildFormData(formData, tmpURL, thread, composer, tmpId, options) {
        formData.append("thread_id", thread.id);
        formData.append("tmp_url", tmpURL);
        formData.append("thread_model", thread.model);
        formData.append("is_pending", Boolean(composer || options?.detached));
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
    dependencies: ["file_upload", "mail.store"],
    start(env, services) {
        return new AttachmentUploadService(env, services);
    },
};

registry.category("services").add("mail.attachment_upload", attachmentUploadService);
