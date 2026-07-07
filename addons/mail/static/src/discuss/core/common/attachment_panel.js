import { DateSection } from "@mail/core/common/date_section";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { AttachmentList } from "@mail/core/common/attachment_list";

import { Component, signal, t, useOnChange } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { propComputed, useSequential, useVisible } from "@mail/utils/common/hooks";

export class AttachmentPanel extends Component {
    static components = { ActionPanel, AttachmentList, DateSection };
    static template = "mail.AttachmentPanel";

    loadOlderRef = signal.ref();

    setup() {
        super.setup();
        this.sequential = useSequential();
        this.store = useService("mail.store");
        this.channel = propComputed("channel", t.instanceOf(this.store["discuss.channel"]));
        this.close = propComputed("close", t.function([]).optional());
        this.offlineService = useService("offline");
        this.ormService = useService("orm");
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.unlinkAttachment = this.unlinkAttachment.bind(this);
        useOnChange(
            () => [this.channel()],
            (channel) => channel.fetchMoreAttachments()
        );
        useVisible(this.loadOlderRef, (isVisible) => {
            if (isVisible) {
                this.channel().fetchMoreAttachments();
            }
        });
    }

    /**
     * @return {Object<string, import("models").Attachment[]>}
     */
    get attachmentsByDate() {
        const attachmentsByDate = {};
        for (const attachment of this.channel().sortedAttachments) {
            const attachments = attachmentsByDate[attachment.monthYear] ?? [];
            attachments.push(attachment);
            attachmentsByDate[attachment.monthYear] = attachments;
        }
        return attachmentsByDate;
    }

    /** @type {ReturnType<typeof import("@mail/core/common/attachment_list").unlinkAttachmentType>["type"]} */
    unlinkAttachment({ attachment }) {
        this.attachmentUploadService.unlink(attachment);
    }
}
