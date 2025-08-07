import { getNonEditableMentions, parseEmail } from "@mail/utils/common/format";
import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";
import { renderToMarkup } from "@web/core/utils/render";
import { rpc } from "@web/core/network/rpc";

export function messageActionOpenFullComposer(title, context, component) {
    const message = component.props.message;
    const thread = component.props.thread;
    const action = {
        name: title,
        type: "ir.actions.act_window",
        res_model: "mail.compose.message",
        view_mode: "form",
        views: [[false, "form"]],
        target: "new",
        context: {
            ...context,
            default_model: thread.model,
            default_res_ids: [thread.id],
            default_subject: message.subject || message.default_subject,
            default_subtype_xmlid: "mail.mt_comment",
        },
    };
    component.env.services.action.doAction(action, {
        onClose: () => thread.fetchNewMessages(),
    });
}

messageActionsRegistry
    .add("reply-all", {
        condition: (component) => component.props.message.canReplyAll(component.props.thread),
        icon: "fa fa-reply",
        iconLarge: "fa fa-lg fa-reply",
        name: _t("Reply All"),
        onSelected: async (component) => {
            const message = component.props.message;
            const thread = component.props.thread;
            const recipients = await rpc("/mail/thread/recipients", {
                thread_model: thread.model,
                thread_id: thread.id,
                message_id: message.id,
            });
            const recipientIds = recipients.map((r) => r.id);
            const emailFrom = message.author_id?.email || message.email_from;
            const [name, email] = parseEmail(emailFrom);
            const datetime = _t("%(date)s at %(time)s", {
                date: message.datetime.toFormat("ccc, MMM d, yyyy"),
                time: message.datetime.toFormat("hh:mm a"),
            });
            const body = renderToMarkup("mail.Message.bodyInReply", {
                body: getNonEditableMentions(message.body),
                date: datetime,
                email,
                message,
                name: name || email,
            });
            const context = {
                default_body: body,
                default_composition_mode: "comment",
                default_composition_comment_option: "reply_all",
                default_partner_ids: recipientIds,
            };
            messageActionOpenFullComposer(_t("Reply All"), context, component);
        },
        sequence: 71,
    })
    .add("forward", {
        condition: (component) => component.props.message.canForward(component.props.thread),
        icon: "fa fa-share",
        iconLarge: "fa fa-lg fa-share",
        name: _t("Forward"),
        onSelected: async (component) => {
            const message = component.props.message;
            const emailFrom = message.author_id?.email || message.email_from;
            const [name, email] = parseEmail(emailFrom);
            const datetime = _t("%(date)s at %(time)s", {
                date: message.datetime.toFormat("ccc, MMM d, yyyy"),
                time: message.datetime.toFormat("hh:mm a"),
            });
            const body = renderToMarkup("mail.Message.bodyInForward", {
                body: getNonEditableMentions(message.body),
                date: datetime,
                email,
                message,
                name: name || email,
            });
            const attachmentIds = message.attachment_ids.map((a) => a.id);
            const newAttachmentIds = await component.env.services.orm.call(
                "ir.attachment",
                "copy",
                [attachmentIds],
                {
                    default: { res_model: "mail.compose.message", res_id: 0 },
                }
            );
            const context = {
                default_attachment_ids: newAttachmentIds,
                default_body: body,
                default_composition_mode: "comment",
                default_composition_comment_option: "forward",
            };
            messageActionOpenFullComposer(_t("Forward Message"), context, component);
        },
        sequence: 72,
    });
