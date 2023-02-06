/* @odoo-module */

export class Attachment {
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;
    accessToken;
    checksum;
    extension;
    filename;
    id;
    mimetype;
    name;
    originThreadLocalId;
    type;
    url;
    /** @type {boolean} */
    uploading;

    /** @type {import("@mail/new/core/thread_model").Thread} */
    get originThread() {
        return this._store.threads[this.originThreadLocalId];
    }

    get displayName() {
        return this.name || this.filename;
    }

    get isText() {
        const textMimeType = [
            "application/javascript",
            "application/json",
            "text/css",
            "text/html",
            "text/plain",
        ];
        return textMimeType.includes(this.mimetype);
    }

    get isPdf() {
        return this.mimetype === "application/pdf";
    }

    get isImage() {
        const imageMimetypes = [
            "image/bmp",
            "image/gif",
            "image/jpeg",
            "image/png",
            "image/svg+xml",
            "image/tiff",
            "image/x-icon",
        ];
        return imageMimetypes.includes(this.mimetype);
    }

    get isUrl() {
        return this.type === "url" && this.url;
    }

    get isUrlYoutube() {
        return !!this.url && this.url.includes("youtu");
    }

    get isVideo() {
        const videoMimeTypes = ["audio/mpeg", "video/x-matroska", "video/mp4", "video/webm"];
        return videoMimeTypes.includes(this.mimetype);
    }

    get isViewable() {
        return (
            (this.isText || this.isImage || this.isVideo || this.isPdf || this.isUrlYoutube) &&
            !this.uploading
        );
    }

    get imageUrl() {
        if (!this.isImage) {
            return "";
        }
        if (!this.accessToken && this.originThread?.model === "mail.channel") {
            return `/mail/channel/${this.originThread.id}/image/${this.id}`;
        }
        const accessToken = this.accessToken ? `?access_token=${this.accessToken}` : "";
        return `/web/image/${this.id}${accessToken}`;
    }

    get defaultSource() {
        if (this.isImage) {
            return `/web/image/${this.id}?signature=${this.checksum}`;
        }
        if (this.isPdf) {
            const pdf_lib = `/web/static/lib/pdfjs/web/viewer.html?file=`;
            if (!this.accessToken && this.originThread?.model === "mail.channel") {
                return `${pdf_lib}/mail/channel/${this.originThread.id}/attachment/${this.id}`;
            }
            const accessToken = this.accessToken ? `?access_token%3D${this.accessToken}` : "";
            return `${pdf_lib}/web/content/${this.id}${accessToken}`;
        }
        if (this.isUrlYoutube) {
            const urlArr = this.url.split("/");
            let token = urlArr[urlArr.length - 1];
            if (token.includes("watch")) {
                token = token.split("v=")[1];
                const amp = token.indexOf("&");
                if (amp !== -1) {
                    token = token.substring(0, amp);
                }
            }
            return `https://www.youtube.com/embed/${token}`;
        }
        if (!this.accessToken && this.originThread?.model === "mail.channel") {
            return `/mail/channel/${this.originThread.id}/attachment/${this.id}`;
        }
        const accessToken = this.accessToken ? `?access_token=${this.accessToken}` : "";
        return `/web/content/${this.id}${accessToken}`;
    }

    get downloadUrl() {
        if (!this.accessToken && this.originThread?.model === "mail.channel") {
            return `/mail/channel/${this.originThread.id}/attachment/${this.id}?download=true`;
        }
        const accessToken = this.accessToken ? `access_token=${this.accessToken}&` : "";
        return `/web/content/ir.attachment/${this.id}/datas?${accessToken}download=true`;
    }
}
