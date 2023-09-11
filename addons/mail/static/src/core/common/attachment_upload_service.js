/* @odoo-module */

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
        this.bus = new EventBus();
        this.fileUploadService = services["file_upload"];
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        this.notificationService = services["notification"];
        /** @type {import("@mail/core/common/attachment_service").AttachmentService} */
        this.attachmentService = services["mail.attachment"];

        this.abortByAttachmentId = new Map();
        this.deferredByAttachmentId = new Map();
        this.composerByUploadingId = new Map();

        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_ADDED",
            ({ detail: { upload } }) => {
                const tmpId = parseInt(upload.data.get("temporary_id"));
                if (!this.composerByUploadingId.has(tmpId)) {
                    return;
                }
                const threadId = parseInt(upload.data.get("thread_id"));
                const threadModel = upload.data.get("thread_model");
                const tmpUrl = upload.data.get("tmp_url");
                const originThread = this.store.Thread.insert({
                    model: threadModel,
                    id: threadId,
                });
                this.abortByAttachmentId.set(tmpId, upload.xhr.abort.bind(upload.xhr));
                const composer = this.composerByUploadingId.get(tmpId);
                const attachment = this.store.Attachment.insert(
                    this._makeAttachmentData(
                        upload,
                        tmpId,
                        composer ? undefined : originThread,
                        tmpUrl
                    )
                );
                if (composer) {
                    composer.attachments.push(attachment);
                }
            }
        );
        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_LOADED",
            ({ detail: { upload } }) => {
                const tmpId = parseInt(upload.data.get("temporary_id"));
                if (!this.composerByUploadingId.has(tmpId)) {
                    return;
                }
                this.abortByAttachmentId.delete(tmpId);
                const composer = this.composerByUploadingId.get(tmpId);
                this.composerByUploadingId.delete(tmpId);
                if (upload.xhr.status === 413) {
                    this.notificationService.add(_t("File too large"), { type: "danger" });
                    return;
                }
                if (upload.xhr.status !== 200) {
                    this.notificationService.add(_t("Server error"), { type: "danger" });
                    return;
                }
                const response = JSON.parse(upload.xhr.response);
                if (response.error) {
                    this.notificationService.add(response.error, { type: "danger" });
                    return;
                }
                const threadId = parseInt(upload.data.get("thread_id"));
                const threadModel = upload.data.get("thread_model");
                const originThread = this.store.Thread.get({ model: threadModel, id: threadId });
                const attachment = this.store.Attachment.insert({
                    ...response,
                    extension: upload.title.split(".").pop(),
                    originThread: composer ? undefined : originThread,
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
                this.unlink(this.store.Attachment.get(tmpId));
                if (def) {
                    def.resolve(attachment);
                    this.deferredByAttachmentId.delete(tmpId);
                }
                this.bus.trigger("FILE_UPLOADED", upload);
            }
        );
        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_ERROR",
            ({ detail: { upload } }) => {
                const tmpId = parseInt(upload.data.get("temporary_id"));
                if (!this.composerByUploadingId.has(tmpId)) {
                    return;
                }
                this.abortByAttachmentId.delete(tmpId);
                this.deferredByAttachmentId.delete(tmpId);
                this.composerByUploadingId.delete(tmpId);
            }
        );
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
        await this.attachmentService.delete(attachment);
    }

    get uploadURL() {
        return "/mail/attachment/upload";
    }

    async uploadFile(thread, composer, file, options) {
        const tmpId = nextId--;
        this.composerByUploadingId.set(tmpId, composer);
        await this.fileUploadService
            .upload(this.uploadURL, [file], {
                buildFormData: (formData) => {
                    this._makeFormData(formData, file, thread, composer, tmpId, options);
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

    _makeFormData(formData, file, thread, composer, tmpId, options) {
        formData.append("thread_id", thread.id);
        formData.append("tmp_url", URL.createObjectURL(file));
        formData.append("thread_model", thread.model);
        formData.append("is_pending", Boolean(composer));
        formData.append("temporary_id", tmpId);
        return formData;
    }

    _makeAttachmentData(upload, tmpId, originThread, tmpUrl) {
        const attachmentData = {
            filename: upload.title,
            id: tmpId,
            mimetype: upload.type,
            name: upload.title,
            originThread: originThread,
            extension: upload.title.split(".").pop(),
            uploading: true,
            tmpUrl,
        };
        return attachmentData;
    }
}

export const attachmentUploadService = {
    dependencies: ["file_upload", "mail.attachment", "mail.store", "notification"],
    start(env, services) {
        return new AttachmentUploadService(env, services);
    },
};

registry.category("services").add("mail.attachment_upload", attachmentUploadService);
