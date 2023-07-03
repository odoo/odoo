/* @odoo-module */

import { AttachmentList } from "@mail/core/common/attachment_list";
import { serverDateToLocalDateShortFormat } from "@mail/utils/common/format";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/web/completed_activity_model").Activity} activity
 * @extends {Component<Props, Env>}
 */
export class CompletedActivity extends Component {
    static components = {
        AttachmentList,
    };
    static props = ["activity", "largeIcon?"];
    static template = "mail.CompletedActivity";

    setup() {
        this.store = useState(useService("mail.store"));
    }

    get attachments() {
        return Object.values(this.store.Attachment.records)
            .filter((attachment) => this.props.activity.attachment_ids.includes(attachment.id))
            .sort(function (a, b) {
                return a.id < b.id ? 1 : -1;
            });
    }

    get dateCompletionFormatted() {
        return serverDateToLocalDateShortFormat(this.props.activity.date_done, { zone: 'utc' });
    }
}
