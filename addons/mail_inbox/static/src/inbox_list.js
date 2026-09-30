/** @odoo-module */
// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { Component } from "@odoo/owl";
import { InboxMailItem } from "./inbox_mail_item";

const FOLDER_LABELS = {
    new: "Inbox",
    starred: "Starred",
    draft: "Drafts",
    sent: "Sent",
    scheduled: "Scheduled",
};

export class InboxList extends Component {
    static template = "mail_inbox.InboxList";
    static components = { InboxMailItem };
    static props = {
        mails: Array,
        loading: Boolean,
        folder: String,
        onMailUpdated: Function,
    };

    get folderLabel() {
        return FOLDER_LABELS[this.props.folder] || this.props.folder;
    }
}
