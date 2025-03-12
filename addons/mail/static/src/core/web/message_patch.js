import { Message } from "@mail/core/common/message";
import { getNonEditableMentions, parseEmail } from "@mail/utils/common/format";
import { markEventHandled } from "@web/core/utils/misc";
import { renderToMarkup } from "@web/core/utils/render";

import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import {
    formatChar,
    formatFloat,
    formatInteger,
    formatMonetary,
    formatText,
} from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.avatarCard = usePopover(AvatarCardPopover);
    },
    get authorAvatarAttClass() {
        return {
            ...super.authorAvatarAttClass,
            "o_redirect cursor-pointer": this.hasAuthorClickable(),
        };
    },
    getAuthorAttClass() {
        return {
            ...super.getAuthorAttClass(),
            "cursor-pointer o-hover-text-underline": this.hasAuthorClickable(),
        };
    },
    getAuthorText() {
        return this.hasAuthorClickable() ? _t("Open card") : undefined;
    },
    getAvatarContainerAttClass() {
        return {
            ...super.getAvatarContainerAttClass(),
            "cursor-pointer": this.hasAuthorClickable(),
        };
    },
    hasAuthorClickable() {
        return this.message.author?.userId;
    },
    onClickAuthor(ev) {
        if (this.hasAuthorClickable()) {
            markEventHandled(ev, "Message.ClickAuthor");
            const target = ev.currentTarget;
            if (!this.avatarCard.isOpen) {
                this.avatarCard.open(target, {
                    id: this.message.author.userId,
                });
            }
        }
    },

    async onClickMessageForward() {
        const email_from = this.message.author?.email
            ? this.message.author.email
            : this.message.email_from;
        const [name, email] = parseEmail(email_from);
        const datetimeFormatted = _t("%(date)s at %(time)s", {
            date: this.message.datetime.toFormat("ccc, MMM d, yyyy"),
            time: this.message.datetime.toFormat("hh:mm a"),
        });

        const body = renderToMarkup("mail.Message.bodyInForward", {
            body: getNonEditableMentions(this.message.body),
            date: datetimeFormatted,
            email,
            message: this.message,
            name: name || email,
        });

        const attachmentIds = this.message.attachment_ids.map((attachment) => attachment.id);
        const newAttachmentIds = await this.env.services.orm.call(
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
        this.openFullComposer(_t("Forward message"), context);
    },

    async onClickMessageReplyAll() {
        const partners = await rpc("/mail/thread/recipients", {
            thread_model: this.props.thread.model,
            thread_id: this.props.thread.id,
            message_id: this.message.id,
        });
        const recipientIds = partners.map((data) => data.id);
        const email_from = this.message.author?.email
            ? this.message.author.email
            : this.message.email_from;
        const [name, email] = parseEmail(email_from);
        const datetimeFormatted = _t("%(date)s at %(time)s", {
            date: this.message.datetime.toFormat("ccc, MMM d, yyyy"),
            time: this.message.datetime.toFormat("hh:mm a"),
        });

        const body = renderToMarkup("mail.Message.bodyInReply", {
            body: getNonEditableMentions(this.message.body),
            date: datetimeFormatted,
            email,
            message: this.message,
            name: name || email,
        });

        const context = {
            default_body: body,
            default_composition_mode: "comment",
            default_composition_comment_option: "reply_all",
            default_partner_ids: recipientIds,
        };
        this.openFullComposer(_t("Reply All"), context);
    },

    openFullComposer(name, context) {
        const actionContext = {
            ...context,
            default_model: this.props.thread.model,
            default_res_ids: [this.props.thread.id],
            default_subject: this.message.subject || this.message.default_subject,
            default_subtype_xmlid: "mail.mt_comment",
        };
        const action = {
            name: name,
            type: "ir.actions.act_window",
            res_model: "mail.compose.message",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: actionContext,
        };
        this.env.services.action.doAction(action, {
            onClose: () => {
                this.props.thread.fetchNewMessages();
            },
        });
    },

    openRecord() {
        this.message.thread.open({ focus: true });
        this.message.thread.highlightMessage = this.message;
    },

    /**
     * @returns {string}
     */
    formatTracking(trackingType, trackingValue) {
        switch (trackingType) {
            case "boolean":
                return trackingValue.value ? _t("Yes") : _t("No");
            /**
             * many2one formatter exists but is expecting id/display_name or data
             * object but only the target record name is known in this context.
             *
             * Selection formatter exists but requires knowing all
             * possibilities and they are not given in this context.
             */
            case "char":
            case "many2one":
            case "selection":
                return formatChar(trackingValue.value);
            case "date": {
                const value = trackingValue.value
                    ? deserializeDate(trackingValue.value)
                    : trackingValue.value;
                return formatDate(value);
            }
            case "datetime": {
                const value = trackingValue.value
                    ? deserializeDateTime(trackingValue.value)
                    : trackingValue.value;
                return formatDateTime(value);
            }
            case "float":
                return formatFloat(trackingValue.value);
            case "integer":
                return formatInteger(trackingValue.value);
            case "text":
                return formatText(trackingValue.value);
            case "monetary":
                return formatMonetary(trackingValue.value, {
                    currencyId: trackingValue.currencyId,
                });
            default:
                return trackingValue.value;
        }
    },

    /**
     * @returns {string}
     */
    formatTrackingOrNone(trackingType, trackingValue) {
        const formattedValue = this.formatTracking(trackingType, trackingValue);
        return formattedValue || _t("None");
    },
});
