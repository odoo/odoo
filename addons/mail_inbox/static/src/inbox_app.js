/** @odoo-module */
// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { InboxSidebar } from "./inbox_sidebar";
import { InboxList } from "./inbox_list";

export const INBOX_FOLDERS = [
    { id: "new", name: "Inbox", icon: "fa-inbox" },
    { id: "starred", name: "Starred", icon: "fa-star" },
    { id: "draft", name: "Drafts", icon: "fa-file-text-o" },
    { id: "sent", name: "Sent", icon: "fa-paper-plane-o" },
    { id: "scheduled", name: "Scheduled", icon: "fa-clock-o" },
];

export class InboxApp extends Component {
    static template = "mail_inbox.InboxApp";
    static components = { InboxSidebar, InboxList };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.folders = INBOX_FOLDERS;
        this.state = useState({
            activeFolder: "new",
            mails: [],
            loading: false,
            counts: {},
        });
        onWillStart(() => this._loadAll());
    }

    async _loadAll() {
        await Promise.all([this._loadMails(), this._loadCounts()]);
    }

    async _loadMails() {
        this.state.loading = true;
        try {
            const domain = this._getDomain(this.state.activeFolder);
            const mails = await this.orm.searchRead(
                "fetchmail.mail",
                domain,
                ["id", "email_from", "author_id", "subject", "preview", "date",
                 "mail_status", "mail_type", "is_starred", "tag_ids", "model", "res_id"],
                { order: "date desc", limit: 50 },
            );
            // Resolve tag IDs to full objects for display
            const allTagIds = [...new Set(mails.flatMap((m) => m.tag_ids))];
            const tagMap = {};
            if (allTagIds.length) {
                const tags = await this.orm.searchRead(
                    "fetchmail.tag",
                    [["id", "in", allTagIds]],
                    ["id", "name", "color"],
                );
                for (const tag of tags) {
                    tagMap[tag.id] = tag;
                }
            }
            this.state.mails = mails.map((m) => ({
                ...m,
                tag_ids: m.tag_ids.map((id) => tagMap[id]).filter(Boolean),
            }));
        } finally {
            this.state.loading = false;
        }
    }

    async _loadCounts() {
        const counts = {};
        for (const folder of INBOX_FOLDERS) {
            counts[folder.id] = await this.orm.searchCount(
                "fetchmail.mail",
                this._getDomain(folder.id),
            );
        }
        this.state.counts = counts;
    }

    _getDomain(folder) {
        if (folder === "new") {
            return [["mail_type", "=", "incoming"], ["mail_status", "=", "new"]];
        }
        if (folder === "starred") {
            return [["is_starred", "=", true]];
        }
        if (folder === "draft") {
            return [["mail_type", "=", "outgoing"], ["mail_status", "=", "draft"]];
        }
        if (folder === "sent") {
            return [["mail_type", "=", "outgoing"], ["mail_status", "=", "sent"]];
        }
        if (folder === "scheduled") {
            return [["mail_type", "=", "outgoing"], ["mail_status", "=", "outgoing"]];
        }
        return [];
    }

    async onSelectFolder(folderId) {
        this.state.activeFolder = folderId;
        await this._loadMails();
    }

    async onMailUpdated() {
        await this._loadAll();
    }
}

registry.category("actions").add("mail_inbox.InboxApp", InboxApp);
