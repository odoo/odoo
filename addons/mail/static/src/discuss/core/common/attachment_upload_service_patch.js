import { AttachmentUploadService } from "@mail/core/common/attachment_upload_service";

import { patch } from "@web/core/utils/patch";

patch(AttachmentUploadService.prototype, {
    setup() {
        super.setup(...arguments);
        this.env.services["bus_service"].subscribe("mail.record/insert", ({ Thread }) => {
            if (
                Thread &&
                "allow_public_upload" in Thread &&
                !Thread.allow_public_upload &&
                !this.store.self.isInternalUser
            ) {
                const attachments = [...this.store.Thread.insert(Thread).composer.attachments];
                for (const attachment of attachments) {
                    this.unlink(attachment);
                }
            }
        });
    },
});
