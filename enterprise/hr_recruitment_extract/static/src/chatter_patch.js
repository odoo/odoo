/* @odoo-module */

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.attachmentUploadService = useService("mail.attachment_upload");
        const thread = this.store.Thread.insert({
            model: this.props.threadModel,
            id: this.props.threadId,
        });
        this.attachmentUploadService.onFileUploaded(thread, () => {
            if (this.state.thread?.model === "hr.candidate") {
                this.reloadParentView();
            }
        });
    },
});
