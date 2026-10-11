import { Attachment } from "@mail/core/common/attachment_model";
import { patchModel } from "@mail/model/export";
import { location } from "@web/core/browser/browser";
import { session } from "@web/session";

/**
 * PDF previews are not supported across origins for now, as the pdfjs viewer
 * is rooted to the current domain and cannot be properly embedded cross-origin.
 *
 * @typedef {string} ExternalLivechatDisabledPdfReason
 */
export const attachmentPatch = patchModel(Attachment, {
    get isViewable() {
        if (this.isPdf && location.origin !== session.origin) {
            return false;
        }
        return super.isViewable;
    },
});
