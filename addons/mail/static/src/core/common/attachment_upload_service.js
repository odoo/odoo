import { EventBus, usePlugin } from "@odoo/owl";
import { FileUploadPlugin } from "@web/core/file_upload/file_upload_plugin";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { registry } from "@web/core/registry";

export class AttachmentUploadService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        /** @type {import("@mail/core/common/store_plugin").Store} */
        this.store = services["mail.store"];
        this.notificationService = usePlugin(NotificationPlugin);
        this.fileUpload = usePlugin(FileUploadPlugin);

        this.nextId = -1;
        this.abortByAttachmentId = new Map();
        /** @type {Map<number, (value?: void) => void} */
        this.resolveUploadByAttachmentId = new Map();
        this.deletingAttachmentIds = new Set();
        this.uploadingAttachmentIds = new Set();
        this._fileUploadBus = new EventBus();
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

    _cleanupUploading(tmpId) {
        this.abortByAttachmentId.delete(tmpId);
        this.resolveUploadByAttachmentId.delete(tmpId);
        this.uploadingAttachmentIds.delete(tmpId);
        this.store["ir.attachment"].get(tmpId)?.delete();
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
        this.uploadingAttachmentIds.add(tmpId);
        const { promise: uploadPromise, resolve: resolveUpload } = Promise.withResolvers();
        this.resolveUploadByAttachmentId.set(tmpId, resolveUpload);
        const formData = new FormData();
        this._buildFormData(formData, tmpURL, thread, composer, tmpId, options);
        const controller = new AbortController();
        this.abortByAttachmentId.set(tmpId, () => controller.abort());
        const attachment = this.store["ir.attachment"].insert(
            this._makeAttachmentData(file, tmpId, composer ? undefined : thread, tmpURL, formData)
        );
        composer?.attachments.push(attachment);
        let response;
        try {
            response = await this.fileUpload.sendFiles(
                this.getUploadURL(thread),
                { ...Object.fromEntries(formData), ufile: [file] },
                { signal: controller.signal }
            );
        } catch (error) {
            this.notificationService.add(error.message, { type: "danger" });
        }
        if (!this.uploadingAttachmentIds.has(tmpId)) {
            return uploadPromise;
        }
        if (response) {
            this._processLoaded(thread, composer, response, tmpId, resolveUpload);
        } else {
            resolveUpload();
            this._cleanupUploading(tmpId);
        }
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

    _makeAttachmentData(file, tmpId, thread, tmpUrl) {
        const attachmentData = {
            id: tmpId,
            mimetype: file.type,
            name: file.name,
            thread,
            extension: file.name.split(".").pop(),
            uploading: true,
            tmpUrl,
        };
        return attachmentData;
    }
}

export const attachmentUploadService = {
    dependencies: ["mail.store"],
    start(env, services) {
        return new AttachmentUploadService(env, services);
    },
};

registry.category("services").add("mail.attachment_upload", attachmentUploadService);
