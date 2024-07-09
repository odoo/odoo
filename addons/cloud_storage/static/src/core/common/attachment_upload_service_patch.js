import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

patch(AttachmentUploadService.prototype, {
    setup(env, services) {
        super.setup(env, services);
        this.uploadingCloudFiles = new Map();
    },

    _processLoaded(thread, composer, { data, upload_info }, tmpId, def) {
        if (!upload_info) {
            super._processLoaded(...arguments);
            return;
        }
        function removeAttachment() {
            const { Attachment } = this.store.insert(data);
            const [attachment] = Attachment;
            attachment.remove();
        }
        const xhr = new window.XMLHttpRequest();
        this.abortByAttachmentId.set(tmpId, xhr.abort.bind(xhr));
        const file = this.uploadingCloudFiles.get(tmpId);

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
                def.resolve();
                this._cleanupUploading(tmpId);
                return;
            }
            // google returns 200, azure returns 201
            if (xhr.status !== upload_info.response_status) {
                this.notificationService.add(_t("Cloud storage error"), { type: "danger" });
                removeAttachment();
                def.resolve();
                this._cleanupUploading(tmpId);
                return;
            }
            super._processLoaded(...arguments);
        };

        xhr.onerror = () => {
            if (!this.uploadingAttachmentIds.has(tmpId)) {
                return;
            }
            // usually it is because the CORS config for PUT is disallowed for the cloud storage
            this.notificationService.add(_t("Cloud storage error"), { type: "danger" });
            removeAttachment();
            this._cleanupUploading(tmpId);
        };

        xhr.onabort = () => {
            removeAttachment();
            this._cleanupUploading(tmpId);
        };

        xhr.send(file);
    },

    _cleanupUploading(tmpId) {
        super._cleanupUploading(tmpId);
        this.uploadingCloudFiles.delete(tmpId);
    },

    async _upload(thread, composer, file, options, tmpId, tmpURL) {
        if (
            session.cloud_storage_min_file_size !== undefined &&
            file.size > session.cloud_storage_min_file_size
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
