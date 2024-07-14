/* @odoo-module */

import { Chatter } from "@mail/core/web/chatter";
import { patch } from "@web/core/utils/patch";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.attachmentUploader = useAttachmentUploader(
            this.threadService.getThread(this.props.threadModel, this.props.threadId),
            {
                onFileUploaded: () => {
                    if (this.state.thread?.model === "hr.applicant") {
                        this.reloadParentView();
                    }
                },
            }
        );
    },
});
