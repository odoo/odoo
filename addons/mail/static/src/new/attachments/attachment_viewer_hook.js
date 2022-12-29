/* @odoo-module */

import { onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { AttachmentViewer } from "./attachment_viewer";

let id = 1;

export function useAttachmentViewer() {
    const attachmentViewerId = `mail.attachment_viewer${id++}`;
    /**
     * @param {import("@mail/new/core/attachment_model").Attachment} attachment
     * @param {import("@mail/new/core/attachment_model").Attachment[]} attachments
     */
    function open(attachment, attachments = [attachment]) {
        if (!attachment.isViewable) {
            return;
        }
        if (attachments.length > 0) {
            const viewableAttachments = attachments.filter((attachment) => attachment.isViewable);
            const index = viewableAttachments.indexOf(attachment);
            registry.category("main_components").add(attachmentViewerId, {
                Component: AttachmentViewer,
                props: { attachments: viewableAttachments, startIndex: index, close },
            });
        }
    }

    function close() {
        registry.category("main_components").remove(attachmentViewerId);
    }
    onWillDestroy(close);
    return { open, close };
}
