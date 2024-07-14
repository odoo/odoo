/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { messageActionsRegistry } from "@mail/core/common/message_actions";

messageActionsRegistry.add("closeThread", {
    condition: (component) => component.props.isFirstMessage && component.env.closeThread && !component.env.isResolved,
    icon: "fa-check",
    title: () => _t("Resolve the Thread"),
    onClick: (component) => component.env.closeThread(),
    sequence: 0,
});

messageActionsRegistry.add("openThread", {
    condition: (component) => component.props.isFirstMessage && component.env.openThread && component.env.isResolved,
    icon: "fa-retweet",
    title: () => _t("Reopen the Thread"),
    onClick: (component) => component.env.openThread(),
    sequence: 0,
});
