/* @odoo-module */

import { PartnerImStatus } from "@mail/new/discuss/partner_im_status";
import { AttachmentList } from "@mail/new/attachments/attachment_list";
import { MessageInReplyTo } from "./message_in_reply_to";
import { isEventHandled, markEventHandled } from "@mail/new/utils/misc";
import { convertBrToLineBreak, htmlToTextContentInline } from "@mail/new/utils/format";
import { onExternalClick } from "@mail/new/utils/hooks";
import {
    Component,
    onPatched,
    toRaw,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Composer } from "../composer/composer";
import { useMessaging, useStore } from "../core/messaging_hook";
import { MessageDeleteDialog } from "./message_delete_dialog";
import { LinkPreviewList } from "./link_preview/link_preview_list";
import { RelativeTime } from "./relative_time";
import { MessageReactions } from "./message_reactions";
import { useEmojiPicker } from "../emoji_picker/emoji_picker";
import { usePopover } from "@web/core/popover/popover_hook";
import { MessageNotificationPopover } from "./message_notification_popover";
import { MessageSeenIndicator } from "./message_seen_indicator";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {boolean} [hasActions]
 * @property {boolean} [highlighted]
 * @property {function} [onParentMessageClick]
 * @property {import("@mail/new/core/message_model").Message} message
 * @property {import("@mail/new/utils/hooks").MessageToReplyTo} [messageToReplyTo]
 * @property {boolean} [squashed]
 * @property {import("@mail/new/core/thread_model").Thread} [thread]
 * @extends {Component<Props, Env>}
 */
export class Message extends Component {
    static components = {
        AttachmentList,
        Composer,
        LinkPreviewList,
        MessageInReplyTo,
        MessageReactions,
        MessageSeenIndicator,
        PartnerImStatus,
        RelativeTime,
    };
    static defaultProps = {
        hasActions: true,
        isInChatWindow: false,
        onParentMessageClick: () => {},
    };
    static props = [
        "hasActions?",
        "isInChatWindow?",
        "highlighted?",
        "onParentMessageClick?",
        "message",
        "messageEdition?",
        "messageToReplyTo?",
        "squashed?",
        "thread?",
    ];
    static template = "mail.message";

    setup() {
        this.popover = usePopover();
        this.state = useState({
            isEditing: false,
            isHovered: false,
            isActionListSquashed: this.env.inChatWindow,
        });
        this.root = useRef("root");
        this.messaging = useMessaging();
        this.store = useStore();
        /** @type {import("@mail/new/core/thread_service").ThreadService} */
        this.threadService = useState(useService("mail.thread"));
        /** @type {import("@mail/new/core/message_service").MessageService} */
        this.messageService = useState(useService("mail.message"));
        /** @type {import("@mail/new/attachments/attachment_service").AttachmentService} */
        this.attachmentService = useService("mail.attachment");
        this.user = useService("user");
        useChildSubEnv({
            alignedRight: this.isAlignedRight,
        });
        useEffect(
            (editingMessage) => {
                if (editingMessage === this.props.message) {
                    this.enterEditMode();
                }
            },
            () => [this.props.messageEdition?.editingMessage]
        );
        onExternalClick("root", async (ev) => {
            // Let event be handled by bubbling handlers first.
            await new Promise(setTimeout);
            if (isEventHandled(ev, "emoji.selectEmoji")) {
                return;
            }
            // Stop editing the message on click away.
            if (!this.root.el || ev.target === this.root.el || this.root.el.contains(ev.target)) {
                return;
            }
            if (this.state.isEditing) {
                this.exitEditMode();
            }
        });
        onPatched(() => {
            if (this.props.highlighted && this.root.el) {
                this.root.el.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        });
        if (this.props.hasActions && this.canAddReaction) {
            this.emojiPicker = useEmojiPicker("emoji-picker", {
                onSelect: (emoji) => {
                    const reaction = this.message.reactions.find(
                        ({ content, personas }) =>
                            content === emoji &&
                            personas.find((persona) => persona === this.store.self)
                    );
                    if (!reaction) {
                        this.messageService.react(this.message, emoji);
                    }
                },
            });
        }
    }

    get message() {
        return this.props.message;
    }

    get showSubtypeDescription() {
        return (
            this.message.subtypeDescription &&
            this.message.subtypeDescription.toLowerCase() !==
                htmlToTextContentInline(this.message.body || "").toLowerCase()
        );
    }

    get messageTypeText() {
        if (this.props.message.type === "notification") {
            return _t("System notification");
        }
        if (!this.props.message.isDiscussion && this.props.message.type !== "user_notification") {
            return _t("Note");
        }
        return _t("Message");
    }

    /**
     * @returns {boolean}
     */
    get canAddReaction() {
        return Boolean(!this.message.isTransient && this.message.resId);
    }

    get deletable() {
        return this.editable;
    }

    get editable() {
        if (!this.props.hasActions) {
            return false;
        }
        return this.message.editable;
    }

    get canReplyTo() {
        return (
            this.props.messageToReplyTo &&
            (this.message.needaction || this.message.resModel === "mail.channel")
        );
    }

    /**
     * @returns {boolean}
     */
    get canToggleStar() {
        return Boolean(!this.message.isTransient && this.message.resId);
    }

    /**
     * Determines whether clicking on the author's avatar opens a chat with the
     * author.
     *
     * @returns {boolean}
     */
    get hasOpenChatFeature() {
        if (!this.props.hasActions) {
            return false;
        }
        if (!this.message.author) {
            return false;
        }
        if (this.message.isSelfAuthored) {
            return false;
        }
        return this.props.thread.chatPartnerId !== this.message.author.id;
    }

    get isActive() {
        return this.state.isHovered || this.isClicked || this.emojiPicker?.isOpen;
    }

    get isAlignedRight() {
        return Boolean(
            this.env.inChatWindow && this.user.partnerId === this.props.message.author.id
        );
    }

    get isClicked() {
        /**
         * Depending on whether `isClicked` is called from the JS or from the
         * template, `this` is either the component itself or an object which
         * contains an extra `this` to refer the component.
         */
        const self = this.this ?? this;
        return this.store.clickedMessage && toRaw(this.store.clickedMessage) === self;
    }

    get isOriginThread() {
        if (!this.props.thread) {
            return false;
        }
        return this.message.originThread === this.props.thread;
    }

    get isInInbox() {
        if (!this.props.thread) {
            return false;
        }
        return this.props.thread.id === "inbox";
    }

    onMouseenter() {
        this.state.isHovered = true;
    }

    onMouseleave() {
        this.state.isHovered = false;
        this.store.clickedMessage = null;
    }

    /**
     * @returns {boolean}
     */
    get shouldDisplayAuthorName() {
        if (!this.env.inChatWindow) {
            return true;
        }
        if (this.message.isSelfAuthored) {
            return false;
        }
        if (this.props.thread.type === "chat") {
            return false;
        }
        return true;
    }

    onClickDelete() {
        this.env.services.dialog.add(MessageDeleteDialog, {
            message: this.message,
            messageComponent: Message,
        });
    }

    onClickReplyTo(ev) {
        markEventHandled(ev, "message.replyTo");
        this.props.messageToReplyTo.toggle(this.props.thread, this.props.message);
    }

    async onClickAttachmentUnlink(attachment) {
        await this.attachmentService.delete(attachment);
    }

    openChatAvatar(ev) {
        markEventHandled(ev, "Message.ClickAuthor");
        if (!this.hasOpenChatFeature) {
            return;
        }
        this.threadService.openChat({ partnerId: this.message.author.id });
    }

    /**
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        const model = ev.target.dataset.oeModel;
        const id = Number(ev.target.dataset.oeId);
        if (ev.target.closest(".o_channel_redirect")) {
            ev.preventDefault();
            const thread = this.threadService.insert({ model, id });
            this.threadService.open(thread);
            return;
        }
        if (ev.target.closest(".o_mail_redirect")) {
            ev.preventDefault();
            const partnerId = Number(ev.target.dataset.oeId);
            if (this.user.partnerId !== partnerId) {
                this.threadService.openChat({ partnerId });
            }
            return;
        }
        if (ev.target.tagName === "A") {
            if (model && id) {
                ev.preventDefault();
                this.env.services.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: model,
                    views: [[false, "form"]],
                    res_id: id,
                });
            }
            return;
        }
        if (
            !isEventHandled(ev, "Message.ClickAuthor") &&
            !isEventHandled(ev, "Message.ClickFailure")
        ) {
            if (this.isClicked) {
                this.store.clickedMessage = null;
            } else {
                this.store.clickedMessage = this;
            }
        }
    }

    onClickEdit() {
        this.enterEditMode();
    }

    enterEditMode() {
        const messageContent = convertBrToLineBreak(this.props.message.body);
        this.threadService.insertComposer({
            message: this.props.message,
            textInputContent: messageContent,
            selection: {
                start: messageContent.length,
                end: messageContent.length,
                direction: "none",
            },
        });
        this.state.isEditing = true;
    }

    exitEditMode() {
        this.props.messageEdition?.exitEditMode();
        this.message.composer = null;
        this.state.isEditing = false;
    }

    onClickNotificationIcon(ev) {
        this.popover.add(
            ev.target,
            MessageNotificationPopover,
            { message: this.message },
            { position: "top" }
        );
    }

    onClickFailure(ev) {
        markEventHandled(ev, "Message.ClickFailure");
        this.env.services.action.doAction("mail.mail_resend_message_action", {
            additionalContext: {
                mail_message_to_resend: this.message.id,
            },
        });
    }

    get partnerImStatusClassName() {
        let res = "position-absolute bottom-0 end-0";
        if (this.hasOpenChatFeature) {
            res += " cursor-pointer";
        }
        return res;
    }
}
