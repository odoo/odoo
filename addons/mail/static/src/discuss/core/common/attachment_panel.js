import { DateSection } from "@mail/core/common/date_section";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { AttachmentList } from "@mail/core/common/attachment_list";

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSequential, useVisible } from "@mail/utils/common/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class AttachmentPanel extends Component {
    static components = { ActionPanel, AttachmentList, DateSection };
    static props = ["channel"];
    static template = "mail.AttachmentPanel";

    setup() {
        super.setup();
        this.sequential = useSequential();
        this.store = useService("mail.store");
        this.ormService = useService("orm");
        this.attachmentUploadService = useService("mail.attachment_upload");
        onWillStart(() => {
            this.props.channel.fetchMoreAttachments();
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.channel.notEq(this.props.channel)) {
                nextProps.channel.fetchMoreAttachments();
            }
        });
        useVisible("load-older", (isVisible) => {
            if (isVisible) {
                this.props.channel.fetchMoreAttachments();
            }
        });
    }

    /**
     * @return {Object<string, import("models").Attachment[]>}
     */
    get attachmentsByDate() {
        const attachmentsByDate = {};
        for (const attachment of this.props.channel.attachments) {
            const attachments = attachmentsByDate[attachment.monthYear] ?? [];
            attachments.push(attachment);
            attachmentsByDate[attachment.monthYear] = attachments;
        }
        return attachmentsByDate;
    }
}
