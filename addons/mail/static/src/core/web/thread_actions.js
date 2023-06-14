/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { unstarAllMessages } from "../common/message_service";
import { closeChatWindow } from "../common/chat_window_service";

threadActionsRegistry
    .add("mark-all-read", {
        condition(component) {
            return component.thread?.id === "inbox";
        },
        disabledCondition(component) {
            return component.thread.isEmpty;
        },
        open(component) {
            component.orm.silent.call("mail.message", "mark_all_as_read");
        },
        sequence: 1,
        text: _t("Mark all read"),
    })
    .add("unstar-all", {
        condition(component) {
            return component.thread?.id === "starred";
        },
        disabledCondition(component) {
            return component.thread.isEmpty;
        },
        open(component) {
            unstarAllMessages();
        },
        sequence: 2,
        text: _t("Unstar all"),
    })
    .add("expand-form", {
        condition(component) {
            return component.thread?.type === "chatter" && component.props.chatWindow?.isOpen;
        },
        icon: "fa fa-fw fa-expand",
        name: _t("Open Form View"),
        open(component) {
            component.actionService.doAction({
                type: "ir.actions.act_window",
                res_id: component.thread.id,
                res_model: component.thread.model,
                views: [[false, "form"]],
            });
            closeChatWindow(component.props.chatWindow);
        },
        sequence: 50,
    });
