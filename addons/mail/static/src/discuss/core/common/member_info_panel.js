import { ImStatus } from "@mail/core/common/im_status";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { AttachmentList } from "@mail/core/common/attachment_list";

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { _t } from "@web/core/l10n/translation";

export class CompactAttachmentList extends Component {
    static props = ["thread", "attachmentAction"];
    static template = "discuss.CompactAttachmentList";

    setup() {
        this.fileViewer = useFileViewer();
    }

    getImageUrl(attachment) {
        if (attachment.uploading && attachment.tmpUrl) {
            return attachment.tmpUrl;
        }
        return url(attachment.urlRoute, {
            ...attachment.urlQueryParams,
        });
    }

    get attachments() {
        return !this.env.inDiscussApp
            ? this.props.thread.attachments.slice(0, 3)
            : this.props.thread.attachments.slice(0, 2);
    }

    get attachmentCount() {
        return this.props.thread.attachments.length;
    }

    get attachmentMoreText() {
        return !this.env.inDiscussApp
            ? _t("+ %(count)s more", { count: this.attachmentCount - 3 })
            : _t("+ %(count)s more", { count: this.attachmentCount - 2 });
    }

    openAttachmentPanel() {
        this.props.attachmentAction.open();
    }

    onClickAttachment(attachment) {
        this.fileViewer.open(attachment, this.props.thread.attachments);
    }
}

export class ChannelMemberInfo extends Component {
    static components = { ImStatus, ActionPanel, AttachmentList, CompactAttachmentList };
    static props = ["thread", "attachmentAction"];
    static template = "discuss.ChannelMemberInfo";

    setup() {
        this.rtc = useService("discuss.rtc");
        this.actionsService = useService("action");
    }

    get correspondent() {
        return this.props.thread.correspondent;
    }

    get thread() {
        return this.props.thread;
    }

    openUserRecord() {
        this.actionsService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            views: [[false, "form"]],
            res_id: this.correspondent.persona.id,
        });
    }

    /** List of the keys that define correspondent info */
    get correspondentInfoKeys() {
        return ["email", "phone"];
    }

    get correspondentInfo() {
        return this.correspondentInfoKeys.map((key) => ({
            key: _t("%(label)s", { label: this._formatKey(key) }),
            value: this.correspondent.persona[key],
        }));
    }

    _formatKey(key) {
        return key.replace(/_/g, "").replace(/\b\w/g, (char) => char.toUpperCase());
    }
}
