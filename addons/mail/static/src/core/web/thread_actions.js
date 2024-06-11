/* @odoo-module */

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

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
            component.messageService.unstarAll();
        },
        sequence: 2,
        setup() {
            const component = useComponent();
            component.messageService = useState(useService("mail.message"));
        },
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
            component.chatWindowService.close(component.props.chatWindow);
        },
        sequence: 50,
    });
