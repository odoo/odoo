/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get isPdf() {
        if (this.documentData && this.documentData.has_embedded_pdf) {
            return true;
        }
        return super.isPdf;
    },

    /**
     * Attachments with embedded pdf must not be
     * classified as both pdf and text (e.g. xml).
     */
    get isText() {
        if (this.documentData && this.documentData.has_embedded_pdf) {
            return false;
        }
        return super.isText;
    },
});
