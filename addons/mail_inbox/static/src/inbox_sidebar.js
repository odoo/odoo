/** @odoo-module */
// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { Component } from "@odoo/owl";

export class InboxSidebar extends Component {
    static template = "mail_inbox.InboxSidebar";
    static props = {
        folders: Array,
        activeFolder: String,
        counts: Object,
        onSelectFolder: Function,
    };

    onFolderClick(folderId) {
        this.props.onSelectFolder(folderId);
    }
}
