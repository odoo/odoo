/** @odoo-module */
// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { Component, useState, useRef, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Format a server datetime string for display (Gmail-like short format).
 * @param {string|false} dateStr
 */
function formatMailDate(dateStr) {
    if (!dateStr) {
        return "";
    }
    const date = new Date(dateStr.replace(" ", "T") + "Z");
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const mailDayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    if (mailDayStart.getTime() === todayStart.getTime()) {
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
    if (date.getFullYear() === now.getFullYear()) {
        return date.toLocaleDateString([], { month: "short", day: "numeric" });
    }
    return date.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
}

/** Dialog to link a fetchmail.mail to an existing Odoo record. */
class LinkToRecordDialog extends Component {
    static template = "mail_inbox.LinkToRecordDialog";
    static components = { Dialog };
    static props = {
        mail: Object,
        close: Function,
        onLinked: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            models: [],
            selectedModel: "",
            records: [],
            selectedRecordId: null,
            loading: false,
        });
        this._loadModels();
    }

    async _loadModels() {
        this.state.models = await this.orm.searchRead(
            "ir.model",
            [["transient", "=", false], ["is_mail_thread", "=", true]],
            ["model", "name"],
            { order: "name asc", limit: 100 },
        );
    }

    async onModelChange(ev) {
        this.state.selectedModel = ev.target.value;
        this.state.selectedRecordId = null;
        this.state.records = [];
        if (this.state.selectedModel) {
            await this._loadRecords("");
        }
    }

    async onRecordSearch(ev) {
        await this._loadRecords(ev.target.value);
    }

    async _loadRecords(search) {
        if (!this.state.selectedModel) {
            return;
        }
        this.state.loading = true;
        try {
            const domain = search ? [["display_name", "ilike", search]] : [];
            this.state.records = await this.orm.searchRead(
                this.state.selectedModel,
                domain,
                ["id", "display_name"],
                { limit: 10 },
            );
        } catch {
            this.state.records = [];
        } finally {
            this.state.loading = false;
        }
    }

    selectRecord(record) {
        this.state.selectedRecordId = record.id;
    }

    async confirm() {
        if (!this.state.selectedModel || !this.state.selectedRecordId) {
            return;
        }
        await this.orm.write("fetchmail.mail", [this.props.mail.id], {
            model: this.state.selectedModel,
            res_id: this.state.selectedRecordId,
        });
        this.props.onLinked();
        this.props.close();
    }
}

/** Dialog to manage tags on a fetchmail.mail record. */
class AddTagDialog extends Component {
    static template = "mail_inbox.AddTagDialog";
    static components = { Dialog };
    static props = {
        mail: Object,
        close: Function,
        onTagged: Function,
    };

    setup() {
        this.orm = useService("orm");
        const currentIds = (this.props.mail.tag_ids || []).map((t) =>
            typeof t === "object" ? t.id : t
        );
        this.state = useState({
            tags: [],
            selected: Object.fromEntries(currentIds.map((id) => [id, true])),
        });
        this._loadTags();
    }

    async _loadTags() {
        this.state.tags = await this.orm.searchRead(
            "fetchmail.tag",
            [],
            ["id", "name"],
            { order: "name asc" },
        );
    }

    toggleTag(id) {
        this.state.selected[id] = !this.state.selected[id];
    }

    async confirm() {
        const ids = Object.entries(this.state.selected)
            .filter(([, v]) => v)
            .map(([k]) => Number(k));
        await this.orm.write("fetchmail.mail", [this.props.mail.id], {
            tag_ids: [[6, 0, ids]],
        });
        this.props.onTagged();
        this.props.close();
    }
}

export class InboxMailItem extends Component {
    static template = "mail_inbox.InboxMailItem";
    static props = {
        mail: Object,
        onMailUpdated: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.action = useService("action");
        this.actionsRef = useRef("actions");
        this._hideTimer = null;
        onWillDestroy(() => clearTimeout(this._hideTimer));
    }

    get mail() {
        return this.props.mail;
    }

    get senderName() {
        const mail = this.mail;
        if (mail.author_id) {
            return Array.isArray(mail.author_id) ? mail.author_id[1] : mail.author_id;
        }
        const match = (mail.email_from || "").match(/^([^<]+)</);
        if (match) {
            return match[1].trim();
        }
        return mail.email_from || "Unknown";
    }

    get formattedDate() {
        return formatMailDate(this.mail.date);
    }

    get isUnread() {
        return this.mail.mail_type === "incoming" && this.mail.mail_status === "new";
    }

    get isRead() {
        return this.mail.mail_type === "incoming" && this.mail.mail_status === "read";
    }

    // --- Popover show/hide (position set once on mouseenter, never updated) ---

    onRowMouseEnter(ev) {
        const el = this.actionsRef.el;
        if (!el) return;
        if (!el.classList.contains("o-visible")) {
            el.style.left = ev.clientX + 16 + "px";
            el.style.top = ev.clientY + "px";
        }
        el.classList.add("o-visible");
        this._cancelHide();
    }

    onRowMouseLeave() {
        this._scheduleHide();
    }

    onActionsMouseEnter() {
        this._cancelHide();
    }

    onActionsMouseLeave() {
        this._scheduleHide();
    }

    _scheduleHide() {
        this._hideTimer = setTimeout(() => {
            this.actionsRef.el?.classList.remove("o-visible");
        }, 150);
    }

    _cancelHide() {
        clearTimeout(this._hideTimer);
        this._hideTimer = null;
    }

    // --- Actions ---

    async markAsRead() {
        await this.orm.write("fetchmail.mail", [this.mail.id], { mail_status: "read" });
        this.actionsRef.el?.classList.remove("o-visible");
        await this.props.onMailUpdated();
    }

    async markAsUnread() {
        await this.orm.write("fetchmail.mail", [this.mail.id], { mail_status: "new" });
        this.actionsRef.el?.classList.remove("o-visible");
        await this.props.onMailUpdated();
    }

    async toggleStar() {
        await this.orm.write("fetchmail.mail", [this.mail.id], {
            is_starred: !this.mail.is_starred,
        });
        await this.props.onMailUpdated();
    }

    async deleteMail() {
        await this.orm.unlink("fetchmail.mail", [this.mail.id]);
        await this.props.onMailUpdated();
    }

    openLinkToRecord() {
        this.actionsRef.el?.classList.remove("o-visible");
        this.dialog.add(LinkToRecordDialog, {
            mail: this.mail,
            onLinked: () => this.props.onMailUpdated(),
        });
    }

    openAddTag() {
        this.actionsRef.el?.classList.remove("o-visible");
        this.dialog.add(AddTagDialog, {
            mail: this.mail,
            onTagged: () => this.props.onMailUpdated(),
        });
    }

    openLinkedRecord() {
        if (this.mail.model && this.mail.res_id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: this.mail.model,
                res_id: this.mail.res_id,
                views: [[false, "form"]],
            });
        }
    }
}
