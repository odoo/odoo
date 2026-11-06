import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

patch(AttachmentUploadService.prototype, {
    setup(env, services) {
        super.setup(env, services);
        this.uploadingCloudFiles = new Map();
        // Abort on pagehide rather than beforeunload, as the user can still
        // decide to stay on the page while messages wait for their uploads.
        window.addEventListener("pagehide", () => {
            // Leaving the page loses the messages waiting for these uploads:
            // discard them, as aborting would post them without their files.
            for (const tmpId of this.abortByAttachmentId.keys()) {
                this.store["ir.attachment"]
                    .get(tmpId)
                    ?.message_ids.find((m) => m.isPending)
                    ?.delete();
            }
            this.abortByAttachmentId.forEach((abort) => abort());
        });
    },

    _processLoaded(thread, composer, { data, upload_info }, tmpId, resolveUpload) {
        if (!upload_info) {
            super._processLoaded(...arguments);
            return;
        }
        const removeAttachment = () => {
            const { store_data, attachment_id } = data;
            this.store.insert(store_data);
            /** @type {import("models").Attachment} */
            const attachment = this.store["ir.attachment"].get(attachment_id);
            attachment.remove();
        }
        const xhr = new window.XMLHttpRequest();
        this.abortByAttachmentId.set(tmpId, xhr.abort.bind(xhr));
        const file = this.uploadingCloudFiles.get(tmpId);

        xhr.upload.addEventListener("progress", (ev) => super._onUploadProgress(tmpId, ev));
        xhr.open(upload_info.method, upload_info.url);
        for (const [key, value] of Object.entries(upload_info.headers || {})) {
            xhr.setRequestHeader(key, value);
        }

        xhr.onload = () => {
            if (!this.uploadingAttachmentIds.has(tmpId)) {
                return;
            }
            if (xhr.status === 403) {
                // usually it is because the token of the server for the cloud storage is expired
                this.notificationService.add(
                    _t("You are not allowed to upload file to the cloud storage"),
                    { type: "danger" }
                );
                removeAttachment();
                resolveUpload();
                this._cleanupUploading(tmpId);
                return;
            }
            // google returns 200, azure returns 201
            if (xhr.status !== upload_info.response_status) {
                this.notificationService.add(_t("Cloud storage error"), { type: "danger" });
                removeAttachment();
                resolveUpload();
                this._cleanupUploading(tmpId);
                return;
            }
            // the message may have been sent meanwhile, detaching the upload from its composer
            const { composer: currentComposer } = this.targetsByTmpId.get(tmpId);
            super._processLoaded(
                thread,
                currentComposer,
                { data, upload_info },
                tmpId,
                resolveUpload
            );
            // the server only received a dummy file
            this.store["ir.attachment"].get(data.attachment_id).file_size = file.size;
        };

        xhr.onerror = () => {
            if (!this.uploadingAttachmentIds.has(tmpId)) {
                return;
            }
            // usually it is because the CORS config for PUT is disallowed for the cloud storage
            this.notificationService.add(_t("Cloud storage error"), { type: "danger" });
            removeAttachment();
            resolveUpload();
            this._cleanupUploading(tmpId);
        };

        xhr.onabort = () => {
            removeAttachment();
            resolveUpload();
            this._cleanupUploading(tmpId);
        };

        xhr.send(file);
    },

    _onUploadProgress(tmpId) {
        // the request to the server only contains a dummy file: the progress is
        // the one of the actual upload to the cloud storage
        if (!this.uploadingCloudFiles.has(tmpId)) {
            super._onUploadProgress(...arguments);
        }
    },

    _makeAttachmentData(_upload, tmpId) {
        const attachmentData = super._makeAttachmentData(...arguments);
        const file = this.uploadingCloudFiles.get(tmpId);
        if (file) {
            attachmentData.file_size = file.size;
        }
        return attachmentData;
    },

    _cleanupUploading(tmpId) {
        super._cleanupUploading(tmpId);
        this.uploadingCloudFiles.delete(tmpId);
    },

    async _upload(thread, composer, file, options, tmpId, tmpURL) {
        if (
            !thread.channel?.ai_agent_id && // ai_agent (enterprise) does not support url files
            session.cloud_storage_min_file_size !== undefined &&
            file.size > session.cloud_storage_min_file_size &&
            !session.cloud_storage_unsupported_models.includes(thread.model)
        ) {
            // store the file in the this.uploadingCloudFiles map
            this.uploadingCloudFiles.set(tmpId, file);
            // replace the file to a dummy file with the same name and type
            // and send the dummy file to the server without real content overhead
            file = new File([new Blob([])], file.name, { type: file.type });
            options = options ? { ...options, cloud_storage: true } : { cloud_storage: true };
        }
        return super._upload(thread, composer, file, options, tmpId, tmpURL);
    },

    _buildFormData(formData, tmpURL, thread, composer, tmpId, options) {
        super._buildFormData(...arguments);
        if (options?.cloud_storage) {
            formData.append("cloud_storage", true);
        }
        return formData;
    },
});
