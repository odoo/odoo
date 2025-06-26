import { url } from "@web/core/utils/urls";

export const FileModelMixin = (T) =>
    class extends T {
        access_token;
        checksum;
        extension;
        filename;
        id;
        mimetype;
        name;
        /** @type {"binary"|"url"} */
        type;
        /** @type {string} */
        tmpUrl;
        /**
         * This URL should not be used as the URL to serve the file. `urlRoute` should be used
         * instead. The server will properly redirect to the correct URL when necessary.
         *
         * @type {string}
         */
        url;
        /** @type {boolean} */
        uploading;

        get defaultSource() {
            const route = url(this.urlRoute, this.urlQueryParams);
            const encodedRoute = encodeURIComponent(route);
            if (this.isPdf) {
                return `/web/static/lib/pdfjs/web/viewer.html?file=${encodedRoute}#pagemode=none`;
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
            return route;
        }

        get displayName() {
            return this.name || this.filename;
        }

        get downloadUrl() {
            return url(this.urlRoute, { ...this.urlQueryParams, download: true });
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
                "image/webp",
            ];
            return imageMimetypes.includes(this.mimetype);
        }

        get isPdf() {
            return this.mimetype && this.mimetype.startsWith("application/pdf");
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

        /**
         * @returns {Object}
         */
        get urlQueryParams() {
            if (this.uploading && this.tmpUrl) {
                return {};
            }
            const params = {
                access_token: this.access_token,
                filename: this.name,
                unique: this.checksum,
            };
            for (const prop in params) {
                if (!params[prop]) {
                    delete params[prop];
                }
            }
            return params;
        }

        /**
         * @returns {string}
         */
        get urlRoute() {
            if (this.uploading && this.tmpUrl) {
                return this.tmpUrl;
            }
            return this.isImage ? `/web/image/${this.id}` : `/web/content/${this.id}`;
        }
    };

export class FileModel extends FileModelMixin(Object) {}
