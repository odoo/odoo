import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

messageActionsRegistry
    .add("reply-all", {
        condition: (component) =>
            component.props.message.canReplyAllandForward(component.props.thread),
        icon: "fa fa-reply",
        title: _t("Reply All"),
        onClick: (component) => {
            component.onClickMessageReplyAll();
        },
        sequence: 71,
    })
    .add("forward", {
        condition: (component) =>
            component.props.message.canReplyAllandForward(component.props.thread),
        icon: "fa fa-share",
        title: _t("Forward"),
        onClick: (component) => {
            component.onClickMessageForward();
        },
        sequence: 72,
    });
