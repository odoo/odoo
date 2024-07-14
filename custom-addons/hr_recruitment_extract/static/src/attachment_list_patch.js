/* @odoo-module */

import { AttachmentList } from "@mail/core/common/attachment_list";
import { patch } from "@web/core/utils/patch";

AttachmentList.props.push("reloadChatterParentView?");

patch(AttachmentList.prototype, {
    onConfirmUnlink(attachment) {
        super.onConfirmUnlink(attachment);
        if (attachment.originThread?.model === "hr.applicant") {
            this.props.reloadChatterParentView();
        }
    },
});
