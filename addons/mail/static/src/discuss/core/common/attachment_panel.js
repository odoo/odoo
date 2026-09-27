import { DateSection } from "@mail/core/common/date_section";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { AttachmentList } from "@mail/core/common/attachment_list";

import { Component, signal, t, useOnChange, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { groupAttachments } from "@mail/utils/common/attachments";
import { useSequential, useVisible } from "@mail/utils/common/hooks";

export class AttachmentPanel extends Component {
    static components = { ActionPanel, AttachmentList, DateSection };
    static template = "mail.AttachmentPanel";

    loadOlderRef = signal.ref();

    setup() {
        super.setup();
        this.sequential = useSequential();
        this.store = useService("mail.store");
        this.props = useProps({
            channel: t.instanceOf(this.store["discuss.channel"]),
            close: t.function([]).optional(),
        });
        this.offlineService = useService("offline");
        this.ormService = useService("orm");
        this.attachmentUploadService = useService("mail.attachment_upload");
        useOnChange(
            () => [this.props.channel],
            (channel) => channel.fetchMoreAttachments()
        );
        useVisible(this.loadOlderRef, (isVisible) => {
            if (isVisible) {
                this.props.channel.fetchMoreAttachments();
            }
        });
    }

    /**
     * @return {Object<string, import("@mail/utils/common/attachments").AttachmentGroup[]>}
     */
    get attachmentGroupsByDate() {
        const attachmentsByDate = {};
        for (const attachment of this.props.channel.sortedAttachments) {
            const attachments = attachmentsByDate[attachment.monthYear] ?? [];
            attachments.push(attachment);
            attachmentsByDate[attachment.monthYear] = attachments;
        }
        return Object.fromEntries(
            Object.entries(attachmentsByDate).map(([date, attachments]) => [
                date,
                groupAttachments(attachments),
            ])
        );
    }
}
