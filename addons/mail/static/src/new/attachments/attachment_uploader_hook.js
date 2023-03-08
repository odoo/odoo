/* @odoo-module */

import { useState } from "@odoo/owl";
import { Deferred } from "@web/core/utils/concurrency";
import { useBus, useService } from "@web/core/utils/hooks";
import { createLocalId } from "@mail/new/utils/misc";
import { _t } from "@web/core/l10n/translation";

function dataUrlToBlob(data, type) {
    const binData = window.atob(data);
    const uiArr = new Uint8Array(binData.length);
    uiArr.forEach((_, index) => (uiArr[index] = binData.charCodeAt(index)));
    return new Blob([uiArr], { type });
}

let nextId = -1;

/**
 * @param {import("@mail/new/core/thread_model").Thread} thread
 * @param {Object} [param1={}]
 * @param {import("@mail/new/composer/composer_model").Composer} [param1.composer]
 * @param {function} [param1.onFileUploaded]
 */
export function useAttachmentUploader(thread, { composer, onFileUploaded } = {}) {
    const { bus, upload } = useService("file_upload");
    const notificationService = useService("notification");
    /** @type {import("@mail/new/core/store_service").Store} */
    const store = useService("mail.store");
    /** @type {import("@mail/new/core/thread_service").ThreadService} */
    const threadService = useService("mail.thread");
    /** @type {import("@mail/new/attachments/attachment_service").AttachmentService} */
    const attachmentService = useService("mail.attachment");
    const abortByAttachmentId = new Map();
    const deferredByAttachmentId = new Map();
    const uploadingAttachmentIds = new Set();
    const state = useState({
        thread,
        uploadData({ data, name, type }) {
            const file = new File([dataUrlToBlob(data, type)], name, { type });
            return this.uploadFile(file);
        },
        async uploadFile(file) {
            const tmpId = nextId--;
            uploadingAttachmentIds.add(tmpId);
            await upload("/mail/attachment/upload", [file], {
                buildFormData(formData) {
                    formData.append("thread_id", state.thread.id);
                    formData.append("tmp_url", URL.createObjectURL(file));
                    formData.append("thread_model", state.thread.model);
                    formData.append("is_pending", Boolean(composer));
                    formData.append("temporary_id", tmpId);
                },
            }).catch((e) => {
                if (e.name !== "AbortError") {
                    throw e;
                }
            });
            const uploadDoneDeferred = new Deferred();
            deferredByAttachmentId.set(tmpId, uploadDoneDeferred);
            return uploadDoneDeferred;
        },
        async unlink(attachment) {
            const abort = abortByAttachmentId.get(attachment.id);
            const def = deferredByAttachmentId.get(attachment.id);
            if (abort) {
                abort();
                def.resolve();
            }
            abortByAttachmentId.delete(attachment.id);
            deferredByAttachmentId.delete(attachment.id);
            await attachmentService.delete(attachment);
        },
        clear() {
            abortByAttachmentId.clear();
            deferredByAttachmentId.clear();
            uploadingAttachmentIds.clear();
        },
    });
    useBus(bus, "FILE_UPLOAD_ADDED", ({ detail: { upload } }) => {
        const tmpId = parseInt(upload.data.get("temporary_id"));
        if (!uploadingAttachmentIds.has(tmpId)) {
            return;
        }
        const threadId = parseInt(upload.data.get("thread_id"));
        const threadModel = upload.data.get("thread_model");
        const tmpUrl = upload.data.get("tmp_url");
        const originThread = threadService.insert({ model: threadModel, id: threadId });
        abortByAttachmentId.set(tmpId, upload.xhr.abort.bind(upload.xhr));
        const attachment = attachmentService.insert({
            filename: upload.title,
            id: tmpId,
            mimetype: upload.type,
            name: upload.title,
            originThread: composer ? undefined : originThread,
            extension: upload.title.split(".").pop(),
            uploading: true,
            tmpUrl,
        });
        if (composer) {
            composer.attachments.push(attachment);
        }
    });
    useBus(bus, "FILE_UPLOAD_LOADED", ({ detail: { upload } }) => {
        const tmpId = parseInt(upload.data.get("temporary_id"));
        if (!uploadingAttachmentIds.has(tmpId)) {
            return;
        }
        uploadingAttachmentIds.delete(tmpId);
        abortByAttachmentId.delete(tmpId);
        if (upload.xhr.status === 413) {
            notificationService.add(_t("File too large"), { type: "danger" });
            return;
        }
        if (upload.xhr.status !== 200) {
            notificationService.add(_t("Server error"), { type: "danger" });
            return;
        }
        const response = JSON.parse(upload.xhr.response);
        if (response.error) {
            notificationService.add(response.error, { type: "danger" });
            return;
        }
        const threadId = parseInt(upload.data.get("thread_id"));
        const threadModel = upload.data.get("thread_model");
        const originThread = store.threads[createLocalId(threadModel, threadId)];
        const attachment = attachmentService.insert({
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
        const def = deferredByAttachmentId.get(tmpId);
        state.unlink(store.attachments[tmpId]);
        if (def) {
            def.resolve(attachment);
            deferredByAttachmentId.delete(tmpId);
        }
        onFileUploaded?.();
    });
    useBus(bus, "FILE_UPLOAD_ERROR", ({ detail: { upload } }) => {
        const tmpId = parseInt(upload.data.get("temporary_id"));
        if (!uploadingAttachmentIds.has(tmpId)) {
            return;
        }
        abortByAttachmentId.delete(tmpId);
        deferredByAttachmentId.delete(tmpId);
        uploadingAttachmentIds.delete(parseInt(upload.data.get("temporary_id")));
    });

    return state;
}
