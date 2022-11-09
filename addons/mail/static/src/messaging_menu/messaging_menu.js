/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { useMessaging } from "../messaging_hook";
import { PartnerImStatus } from "../discuss/partner_im_status";
import { RelativeTime } from "../thread/relative_time";

export class MessagingMenu extends Component {
    static template = "mail.messaging_menu";
    static components = { Dropdown, RelativeTime, PartnerImStatus };
    static props = [];

    setup() {
        this.messaging = useMessaging();
        this.state = useState({
            previews: false,
            filter: "all", // can be 'all', 'channels' or 'chats'
        });
    }

    async loadPreviews() {
        this.state.previews = await this.messaging.fetchPreviews();
    }
    activateTab(ev) {
        const target = ev.target.dataset.tabId;
        if (target) {
            this.state.filter = target;
        }
    }
    get displayedPreviews() {
        const filter = this.state.filter;
        if (filter === "all") {
            return this.state.previews;
        }
        const threads = this.messaging.threads;
        const target = filter === "chats" ? "chat" : "channel";
        return this.state.previews.filter((preview) => {
            return threads[preview.id].type === target;
        });
    }

    openDiscussion(threadId) {
        this.messaging.openDiscussion(threadId);
        this.state.isOpen = false;
        // hack: click on window to close dropdown, because we use a dropdown
        // without dropdownitem...
        document.body.click();
    }

    isAuthor(preview) {
        return preview.last_message.author.id === this.messaging.user.partnerId;
    }

    getPreviewAuthor(id) {
        return this.messaging.partners[id].name;
    }
}

const systrayItem = {
    Component: MessagingMenu,
};

registry.category("systray").add("mail.messaging_menu", systrayItem, { sequence: 25 });
