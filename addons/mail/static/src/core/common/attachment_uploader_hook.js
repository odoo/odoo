/* @odoo-module */

import { useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

function dataUrlToBlob(data, type) {
    const binData = window.atob(data);
    const uiArr = new Uint8Array(binData.length);
    uiArr.forEach((_, index) => (uiArr[index] = binData.charCodeAt(index)));
    return new Blob([uiArr], { type });
}

export class AttachmentUploader {
    constructor(thread, { composer, onFileUploaded } = {}) {
        this.attachmentUploadService = useService("mail.attachment_upload");
        Object.assign(this, { thread, composer, onFileUploaded });
    }

    uploadData({ data, name, type }) {
        const file = new File([dataUrlToBlob(data, type)], name, { type });
        return this.uploadFile(file);
    }

    async uploadFile(file, options) {
        return this.attachmentUploadService.uploadFile(this, file, options);
    }

    async unlink(attachment) {
        await this.attachmentUploadService.unlink(attachment);
    }
}

/**
 * @param {import("models").Thread} thread
 * @param {Object} [param1={}]
 * @param {import("models").Composer} [param1.composer]
 * @param {function} [param1.onFileUploaded]
 */
export function useAttachmentUploader(thread, { composer, onFileUploaded } = {}) {
    return useState(new AttachmentUploader(...arguments));
}
