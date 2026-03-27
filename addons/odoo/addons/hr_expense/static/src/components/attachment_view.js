/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AttachmentView } from "@mail/core/common/attachment_view";

patch(AttachmentView.prototype, {
    get displayName() {
        if (this.state.thread.model === 'hr.expense.sheet') {
            return (this.state.thread.mainAttachment.res_name || this.state.thread.name);
        }
        return super.displayName;
    }
});
