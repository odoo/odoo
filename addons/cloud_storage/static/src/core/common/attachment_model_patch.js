import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

const TEXT_THUMBNAIL_SIZE = 4096;

patch(Attachment.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {string|null|undefined} */
        this.cloudTextUrl = undefined;
        /** @type {string|null|undefined} */
        this.cloudTextThumbnailUrl = undefined;
    },
    get isCloudText() {
        // the server already sends HTML files to the cloud storage URL
        return this.isText && this.mimetype !== "text/html" && this.type === "cloud_storage";
    },
    get isCloudTextInViewer() {
        // the server already sends JSON files to the cloud storage URL in the viewer
        return this.isCloudText && this.mimetype !== "application/json";
    },
    get defaultSource() {
        if (this.isCloudTextInViewer) {
            return this.cloudTextUrl ?? "";
        }
        return super.defaultSource;
    },
    get textThumbnailUrl() {
        if (this.isCloudText) {
            return this.cloudTextThumbnailUrl ?? "";
        }
        return super.textThumbnailUrl;
    },
    delete() {
        if (this.cloudTextUrl) {
            URL.revokeObjectURL(this.cloudTextUrl);
        }
        if (this.cloudTextThumbnailUrl) {
            URL.revokeObjectURL(this.cloudTextThumbnailUrl);
        }
        super.delete();
    },
    async loadCloudTextThumbnail() {
        if (this.cloudTextThumbnailUrl !== undefined) {
            return;
        }
        this.cloudTextThumbnailUrl = null;
        this.cloudTextThumbnailUrl = await this._fetchCloudText({ head: true });
    },
    /**
     * @param {AbortSignal} signal
     */
    async loadCloudText(signal) {
        if (this.cloudTextUrl !== undefined) {
            return;
        }
        this.cloudTextUrl = null;
        const cloudTextUrl = await this._fetchCloudText({ signal });
        if (signal.aborted) {
            if (cloudTextUrl) {
                URL.revokeObjectURL(cloudTextUrl);
            }
            return;
        }
        this.cloudTextUrl = cloudTextUrl;
    },
    unloadCloudText() {
        if (this.cloudTextUrl) {
            URL.revokeObjectURL(this.cloudTextUrl);
        }
        this.cloudTextUrl = undefined;
    },
    /**
     * Get the file from the cloud storage in the browser, as a plain text blob URL.
     *
     * @param {Object} [options]
     * @param {boolean} [options.head] only get the first bytes, for the thumbnail
     * @param {AbortSignal} [options.signal]
     * @returns {Promise<string|null>}
     */
    async _fetchCloudText({ head = false, signal } = {}) {
        try {
            const response = await fetch(url(this.urlRoute, this.urlQueryParams), {
                headers: head ? { Range: `bytes=0-${TEXT_THUMBNAIL_SIZE - 1}` } : {},
                signal,
            });
            if (!response.ok) {
                return null;
            }
            const blob = await response.blob();
            const size = head ? TEXT_THUMBNAIL_SIZE : blob.size;
            return URL.createObjectURL(blob.slice(0, size, "text/plain;charset=utf-8"));
        } catch {
            // the preview stays empty when the cloud storage cannot be reached
            return null;
        }
    },
});
