/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    documentId: null,
    documentData: null,

    get urlRoute() {
        if (this.documentId) {
            return this.isImage
                ? `/web/image/${this.documentId}`
                : `/web/content/${this.documentId}`;
        }
        return super.urlRoute;
    },

    get defaultSource() {
        if (this.isPdf && this.documentId) {
            const encodedRoute = encodeURIComponent(
                `/documents/content/${encodeURIComponent(
                    this.documentData.access_token
                )}?download=0`
            );
            return `/web/static/lib/pdfjs/web/viewer.html?file=${encodedRoute}#pagemode=none`;
        }
        return super.defaultSource;
    },

    get urlQueryParams() {
        const res = super.urlQueryParams;
        if (this.documentId) {
            res["model"] = "documents.document";
            return res;
        }
        return res;
    },
});
