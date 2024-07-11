/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Record } from "./record";

export class DiscussApp extends Record {
    static new(data) {
        /** @type {import("models").DiscussApp} */
        const res = super.new(data);
        Object.assign(res, {
            channels: {
                extraClass: "o-mail-DiscussSidebarCategory-channel",
                id: "channels",
                name: _t("Channels"),
                isOpen: false,
                canView: true,
                canAdd: true,
                serverStateKey: "is_discuss_sidebar_category_channel_open",
                addTitle: _t("Add or join a channel"),
                addHotkey: "c",
            },
            chats: {
                extraClass: "o-mail-DiscussSidebarCategory-chat",
                id: "chats",
                name: _t("Direct messages"),
                isOpen: false,
                canView: false,
                canAdd: true,
                serverStateKey: "is_discuss_sidebar_category_chat_open",
                addTitle: _t("Start a conversation"),
                addHotkey: "d",
            },
        });
        return res;
    }
    /** @returns {import("models").DiscussApp} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").DiscussApp|import("models").DiscussApp[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {'main'|'channel'|'chat'|'livechat'} */
    activeTab = "main";
    chatWindows = Record.many("ChatWindow");
    isActive = false;
    hasRestoredThread = false;
    thread = Record.one("Thread");
    channels = Record.one("DiscussAppCategory");
    chats = Record.one("DiscussAppCategory");
    // mailboxes in sidebar
    inbox = Record.one("Thread");
    starred = Record.one("Thread");
    history = Record.one("Thread");
}

DiscussApp.register();
