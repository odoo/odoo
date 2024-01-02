/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";

let nextUploadId = 1;

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

        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_ADDED",
            ({ detail: { upload } }) => {
                const uploadId = parseInt(upload.data.get("temporary_id"));
                let attachment = this.store.Attachment.get({ uploadId });
                if (!attachment) {
                    return;
                }
                const hooker = attachment.uploadHooker;
                const threadId = parseInt(upload.data.get("thread_id"));
                const threadModel = upload.data.get("thread_model");
                const tmpUrl = upload.data.get("tmp_url");
                const originThread = this.store.Thread.insert({
                    model: threadModel,
                    id: threadId,
                });
                attachment = this.store.Attachment.insert(
                    this._makeAttachmentData(
                        upload,
                        uploadId,
                        hooker.composer ? undefined : originThread,
                        tmpUrl
                    )
                );
                attachment.uploadAbort = upload.xhr.abort.bind(upload.xhr);
                if (hooker.composer) {
                    hooker.composer.attachments.push(attachment);
                }
            }
        );
        this.fileUploadService.bus.addEventListener(
            "FILE_UPLOAD_LOADED",
            ({ detail: { upload } }) => {
                const uploadId = parseInt(upload.data.get("temporary_id"));
                const attachment = this.store.Attachment.get({ uploadId });
                if (!attachment) {
                    return;
                }
                const hooker = attachment.uploadHooker;
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
                attachment.update({
                    ...response,
                    extension: upload.title.split(".").pop(),
                    originThread: hooker.composer ? undefined : originThread,
                });
                attachment.uploadId = false;
                attachment.uploadDoneDeferred?.resolve(attachment);
                hooker.onFileUploaded?.();
            }
        );
    }

    get uploadURL() {
        return "/mail/attachment/upload";
    }

    async unlink(attachment) {
        await attachment.unlink();
    }

    async uploadFile(hooker, file, options) {
        const uploadId = nextUploadId++;
        const attachment = this.store.Attachment.insert({ uploadId });
        attachment.uploadHooker = hooker;
        await this.fileUploadService
            .upload(this.uploadURL, [file], {
                buildFormData: (formData) => {
                    this._makeFormData(formData, file, hooker, uploadId, options);
                },
            })
            .catch((e) => {
                if (e.name !== "AbortError") {
                    throw e;
                }
            });
        attachment.uploadDoneDeferred = new Deferred();
        return attachment.uploadDoneDeferred;
    }

    _makeFormData(formData, file, hooker, uploadId, options) {
        formData.append("thread_id", hooker.thread.id);
        formData.append("tmp_url", URL.createObjectURL(file));
        formData.append("thread_model", hooker.thread.model);
        formData.append("is_pending", Boolean(hooker.composer));
        formData.append("temporary_id", uploadId);
        return formData;
    }

    _makeAttachmentData(upload, uploadId, originThread, tmpUrl) {
        const attachmentData = {
            filename: upload.title,
            uploadId,
            mimetype: upload.type,
            name: upload.title,
            originThread: originThread,
            extension: upload.title.split(".").pop(),
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
