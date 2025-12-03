import { getNonEditableMentions, parseEmail } from "@mail/utils/common/format";
import { registerMessageAction } from "@mail/core/common/message_actions";
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

registerMessageAction("reply-all", {
    condition: ({ message, thread }) => message.canReplyAll(thread),
    icon: "fa fa-reply",
    name: _t("Reply All"),
    onSelected: async ({ message, owner, thread }) => {
        const recipients = await rpc("/mail/thread/recipients", {
            thread_model: thread.model,
            thread_id: thread.id,
            message_id: message.id,
        });
        const recipientIds = recipients.map((r) => r.id);
        const emailFrom = message.author_id?.email || message.email_from;
        const [name, email] = emailFrom ? parseEmail(emailFrom) : ["", ""];
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
            signature: thread.effectiveSelf.main_user_id?.getSignatureBlock(),
        });
        const context = {
            default_body: body,
            default_composition_mode: "comment",
            default_composition_comment_option: "reply_all",
            default_email_add_signature: false,
            default_partner_ids: recipientIds,
        };
        messageActionOpenFullComposer(_t("Reply All"), context, owner);
    },
    sequence: 71,
});
registerMessageAction("forward", {
    condition: ({ message, thread }) => message.canForward(thread),
    icon: "fa fa-share",
    name: _t("Forward"),
    onSelected: async ({ message, owner, store, thread }) => {
        const emailFrom = message.author_id?.email || message.email_from;
        const [name, email] = emailFrom ? parseEmail(emailFrom) : ["", ""];
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
            signature: thread.effectiveSelf.main_user_id?.getSignatureBlock(),
        });
        const attachmentIds = message.attachment_ids.map((a) => a.id);
        const newAttachmentIds = await store.env.services.orm.call(
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
            default_email_add_signature: false,
        };
        messageActionOpenFullComposer(_t("Forward Message"), context, owner);
    },
    sequence: 72,
});
