/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useMessaging } from "@mail/new/messaging_hook";
import { PartnerImStatus } from "@mail/new/discuss/components/partner_im_status";
import { RelativeTime } from "../thread/relative_time";

export class MessagingMenu extends Component {
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
        const threads = this.messaging.state.threads;
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
        return preview.last_message.author.id === this.messaging.state.user.partnerId;
    }

    getPreviewAuthor(id) {
        return this.messaging.state.partners[id].name;
    }
}

Object.assign(MessagingMenu, {
    components: { Dropdown, RelativeTime, PartnerImStatus },
    props: [],
    template: "mail.messaging_menu",
});
