/* @odoo-module */

import {
    ChatWindowService,
    closeChatWindow,
    hideChatWindow,
    openChatWindow,
    showChatWindow,
    toggleFoldChatWindow,
} from "@mail/core/common/chat_window_service";
import { patchFn } from "@mail/utils/common/patch";

import { patch } from "@web/core/utils/patch";

let orm;
let ui;

function notifyChatWindowState(chatWindow) {
    if (ui.isSmall) {
        return;
    }
    if (chatWindow.thread?.model === "discuss.channel") {
        return orm.silent.call("discuss.channel", "channel_fold", [[chatWindow.thread.id]], {
            state: chatWindow.thread.state,
        });
    }
}

patchFn(closeChatWindow, function (chatWindow) {
    this._super(...arguments);
    notifyChatWindowState(chatWindow);
});

patchFn(hideChatWindow, function (chatWindow) {
    this._super(...arguments);
    notifyChatWindowState(chatWindow);
});

patchFn(openChatWindow, function () {
    const chatWindow = this._super(...arguments);
    notifyChatWindowState(chatWindow);
});

patchFn(showChatWindow, function (chatWindow) {
    this._super(...arguments);
    notifyChatWindowState(chatWindow);
});

patchFn(toggleFoldChatWindow, function (chatWindow) {
    this._super(...arguments);
    notifyChatWindowState(chatWindow);
});

patch(ChatWindowService.prototype, "discuss/core/web", {
    setup(env, services) {
        this._super(...arguments);
        ui = services.ui;
        orm = services.orm;
    },
});
