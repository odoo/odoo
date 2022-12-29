/* @odoo-module */

import { useMessaging, useStore } from "@mail/new/core/messaging_hook";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { createLocalId } from "../utils/misc";

export class ThreadIcon extends Component {
    static props = ["thread", "className?"];
    static template = "mail.thread_icon";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
    }

    get chatPartner() {
        if (this.thread.chatPartnerId) {
            return this.store.personas[createLocalId("partner", this.thread.chatPartnerId)];
        }
        return null;
    }

    get classNames() {
        switch (this.thread.type) {
            case "channel":
                if (this.thread.authorizedGroupFullName) {
                    return "fa-hashtag";
                } else {
                    return "fa-globe";
                }
            case "chat":
                switch (this.chatPartner.im_status) {
                    case "online":
                        return "o-mail-thread-icon-online fa-circle";
                    case "offline":
                        return "o-mail-thread-icon-offline fa-circle-o";
                    case "away":
                        return "o-mail-thread-icon-away fa-circle text-warning";
                    case "bot":
                        return "o-mail-thread-icon-bot fa-heart";
                    default:
                        return "o-mail-thread-icon-unknown fa-question-circle";
                }
            case "group":
                return "fa-users";
            case "mailbox":
                switch (this.thread.id) {
                    case "inbox":
                        return "fa-inbox";
                    case "starred":
                        return "fa-star-o";
                    case "history":
                        return "fa-history";
                }
        }
        return "fa-hashtag";
    }

    get thread() {
        return this.store.threads[this.props.thread.localId];
    }

    get titleText() {
        switch (this.thread.type) {
            case "channel":
                if (this.thread.authorizedGroupFullName) {
                    return sprintf(_t('Access restricted to group "%(group name)s"'), {
                        "group name": this.thread.authorizedGroupFullName,
                    });
                } else {
                    return _t("Public Channel");
                }
            case "chat":
                switch (this.chatPartner.im_status) {
                    case "online":
                        return _t("Online");
                    case "offline":
                        return _t("Offline");
                    case "away":
                        return _t("Away");
                    case "bot":
                        return _t("Bot");
                    default:
                        return _t("No IM status available");
                }
            case "group":
                return _t("Grouped Chat");
        }
        return "";
    }
}
