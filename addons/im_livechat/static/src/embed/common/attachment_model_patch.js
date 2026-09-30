import { Attachment } from "@mail/core/common/attachment_model";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

/**
 * PDF previews are not supported across origins for now, as the pdfjs viewer
 * is rooted to the current domain and cannot be properly embedded cross-origin.
 *
 * @typedef {string} ExternalLivechatDisabledPdfReason
 */
patch(Attachment.prototype, {
    get isViewable() {
        if (this.isPdf && browser.location.origin !== session.origin) {
            return false;
        }
        return super.isViewable;
    }
});
