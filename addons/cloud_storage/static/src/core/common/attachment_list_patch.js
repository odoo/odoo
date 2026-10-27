import { AttachmentList } from "@mail/core/common/attachment_list";
import { useOnChange } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(AttachmentList.prototype, {
    setup() {
        super.setup(...arguments);
        useOnChange(
            () =>
                this.props.attachmentGroups
                    .map((group) => group.attachment)
                    .filter((attachment) => attachment.isCloudText),
            (...attachments) => {
                for (const attachment of attachments) {
                    attachment.loadCloudTextThumbnail();
                }
            }
        );
    },
});
