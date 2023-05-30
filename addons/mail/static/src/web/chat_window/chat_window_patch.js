/* @odoo-module */

import { ChatWindow } from "@mail/chat_window/chat_window";
import { ChannelSelector } from "@mail/discuss_app/channel_selector";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(ChatWindow.components, { ChannelSelector });

patch(ChatWindow.prototype, "mail/chat_window", {
    setup() {
        this._super(...arguments);
        this.actionService = useService("action");
    },

    expand() {
        if (this.thread.type === "chatter") {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_id: this.thread.id,
                res_model: this.thread.model,
                views: [[false, "form"]],
            });
            this.chatWindowService.close(this.props.chatWindow);
            return;
        }
        this.threadService.setDiscussThread(this.thread);
        this.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
                name: _t("Discuss"),
            },
            { clearBreadcrumbs: true }
        );
    },

    get actions() {
        const acts = this._super();
        if (this.thread && this.props.chatWindow.isOpen) {
            acts.splice(acts.length - 1, 0, {
                id: "expand",
                name:
                    this.thread.model === "discuss.channel"
                        ? _t("Open in Discuss")
                        : _t("Open Form View"),
                icon: "fa fa-fw fa-expand",
                onSelect: () => this.expand(),
                sequence: 50,
            });
        }
        return acts;
    },
});
