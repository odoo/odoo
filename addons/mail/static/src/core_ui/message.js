/* @odoo-module */

import { ImStatus } from "@mail/discuss_app/im_status";
import { AttachmentList } from "@mail/attachments/attachment_list";
import { MessageInReply } from "./message_in_reply";
import { isEventHandled, markEventHandled } from "@mail/utils/misc";
import { convertBrToLineBreak, htmlToTextContentInline } from "@mail/utils/format";
import { MessageReactionMenu } from "@mail/core_ui/message_reaction_menu";
import {
    Component,
    onMounted,
    onPatched,
    onWillUnmount,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Composer } from "../composer/composer";
import { useMessaging, useStore } from "../core/messaging_hook";
import { MessageConfirmDialog } from "./message_confirm_dialog";
import { LinkPreviewList } from "./link_preview/link_preview_list";
import { RelativeTime } from "./relative_time";
import { MessageReactions } from "./message_reactions";
import { useEmojiPicker } from "../emoji_picker/emoji_picker";
import { usePopover } from "@web/core/popover/popover_hook";
import { MessageNotificationPopover } from "./message_notification_popover";
import { MessageSeenIndicator } from "./message_seen_indicator";
import { _t } from "@web/core/l10n/translation";
import { ActionSwiper } from "@web/core/action_swiper/action_swiper";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { hasTouch } from "@web/core/browser/feature_detection";
import { url } from "@web/core/utils/urls";

/**
 * @typedef {Object} Props
 * @property {boolean} [hasActions]
 * @property {boolean} [highlighted]
 * @property {function} [onParentMessageClick]
 * @property {import("@mail/core/message_model").Message} message
 * @property {import("@mail/utils/hooks").MessageToReplyTo} [messageToReplyTo]
 * @property {boolean} [squashed]
 * @property {import("@mail/core/thread_model").Thread} [thread]
 * @extends {Component<Props, Env>}
 */
export class Message extends Component {
    static components = {
        ActionSwiper,
        AttachmentList,
        Composer,
        Dropdown,
        DropdownItem,
        LinkPreviewList,
        MessageInReply,
        MessageReactions,
        MessageSeenIndicator,
        ImStatus,
        Popover: MessageNotificationPopover,
        RelativeTime,
    };
    static defaultProps = {
        hasActions: true,
        isInChatWindow: false,
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
    static template = "mail.Message";

    setup() {
        this.popover = usePopover(this.constructor.components.Popover, { position: "top" });
        this.state = useState({
            isEditing: false,
            isHovered: false,
            isClicked: false,
            expandOptions: false,
            lastReadMoreIndex: 0,
            isReadMoreByIndex: new Map(),
        });
        this.root = useRef("root");
        this.hasTouch = hasTouch;
        this.messageBody = useRef("body");
        this.messaging = useMessaging();
        this.store = useStore();
        this.rpc = useService("rpc");
        /** @type {import("@mail/core/thread_service").ThreadService} */
        this.threadService = useState(useService("mail.thread"));
        /** @type {import("@mail/core/message_service").MessageService} */
        this.messageService = useState(useService("mail.message"));
        /** @type {import("@mail/attachments/attachment_service").AttachmentService} */
        this.attachmentService = useService("mail.attachment");
        this.user = useService("user");
        this.dialog = useService("dialog");
        this.ui = useState(useService("ui"));
        this.openReactionMenu = this.openReactionMenu.bind(this);
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
        onPatched(() => {
            if (this.props.highlighted && this.root.el) {
                this.root.el.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        });
        this.emojiPickerRef = useRef("emoji-picker");
        if (this.props.hasActions && this.canAddReaction) {
            this.emojiPicker = useEmojiPicker(this.emojiPickerRef, {
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
        onMounted(() => {
            if (this.messageBody.el) {
                $(this.messageBody.el).find(".o-mail-read-more-less").remove();
                this.insertReadMoreLess($(this.messageBody.el));
            }
        });
        onWillUnmount(() => {
            if (this.messageBody.el) {
                $(this.messageBody.el).find(".o-mail-read-more-less").remove();
            }
        });
    }

    get authorAvatarUrl() {
        if (
            this.message.type === "email" &&
            !["partner", "guest"].includes(this.message.author?.type)
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }
        return this.threadService.avatarUrl(this.message.author, this.props.message.originThread);
    }

    get expandText() {
        return _t("Expand");
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
        if (this.props.message.type === "auto_comment") {
            return _t("Automated message");
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
        return (
            this.message.originThread?.allowReactions &&
            Boolean(!this.message.isTransient && this.message.resId)
        );
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
        return this.message.originThread?.allowReplies && this.props.messageToReplyTo;
    }

    /**
     * @returns {boolean}
     */
    get canToggleStar() {
        return Boolean(!this.message.isTransient && this.message.resId);
    }

    get showUnfollow() {
        return Boolean(
            this.message.originThread?.followerOfSelf && this.props.thread?.model === "mail.box"
        );
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
        if (this.store.inPublicPage) {
            return false;
        }
        if (this.message.author.type === "guest") {
            return false;
        }
        return this.props.thread.chatPartnerId !== this.message.author.id;
    }

    get hasAuthorClickable() {
        return this.hasOpenChatFeature && !this.message.isSelfAuthored;
    }

    get isActive() {
        return (
            this.state.isHovered ||
            this.state.isClicked ||
            this.emojiPicker?.isOpen ||
            this.state.expandOptions
        );
    }

    get isAlignedRight() {
        return Boolean(
            !this.env.pinnedPanel &&
                this.env.inChatWindow &&
                this.user.partnerId === this.props.message.author?.id
        );
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
        this.state.isClicked = null;
    }

    /**
     * @returns {boolean}
     */
    get shouldDisplayAuthorName() {
        if (!this.env.inChatWindow || this.env.pinnedPanel) {
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
        this.env.services.dialog.add(MessageConfirmDialog, {
            message: this.message,
            messageComponent: Message,
            prompt: _t("Are you sure you want to delete this message?"),
            onConfirm: () => this.messageService.delete(this.message),
        });
    }

    onClickPin() {
        if (this.message.pinned_at) {
            this.messageService.unpin(this.message);
        } else {
            this.messageService.pin(this.message);
        }
    }

    onClickReplyTo(ev) {
        this.props.messageToReplyTo.toggle(this.props.thread, this.props.message);
    }

    async onClickAttachmentUnlink(attachment) {
        await this.attachmentService.delete(attachment);
    }

    onClickAuthor(ev) {
        if (this.message.author && this.hasAuthorClickable && this.hasOpenChatFeature) {
            this.openChatAvatar(ev);
        }
    }

    onClickMarkAsUnread() {
        const previousMessageId =
            this.message.originThread.getPreviousMessage(this.message)?.id ?? false;
        if (this.props.thread.seen_message_id === previousMessageId) {
            return;
        }
        return this.rpc("/discuss/channel/set_last_seen_message", {
            channel_id: this.message.originThread.id,
            last_message_id: previousMessageId,
            allow_older: true,
        });
    }

    get authorText() {
        return this.hasOpenChatFeature ? _t("Open chat") : "";
    }

    get pinOptionText() {
        return this.message.pinned_at ? _t("Unpin") : _t("Pin");
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
            if (this.state.isClicked) {
                this.state.isClicked = false;
            } else {
                this.state.isClicked = true;
                document.body.addEventListener(
                    "click",
                    () => {
                        this.state.isClicked = false;
                    },
                    { capture: true, once: true }
                );
            }
        }
    }

    onClickEdit() {
        this.enterEditMode();
    }

    enterEditMode() {
        const messageContent = convertBrToLineBreak(this.props.message.body);
        this.threadService.insertComposer({
            mentions: this.props.message.recipients,
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

    onClickNotification(ev) {
        if (this.message.failureNotifications.length > 0) {
            this.onClickFailure(ev);
        } else {
            this.popover.open(ev.target, { message: this.message });
        }
    }

    onClickFailure(ev) {
        markEventHandled(ev, "Message.ClickFailure");
        this.env.services.action.doAction("mail.mail_resend_message_action", {
            additionalContext: {
                mail_message_to_resend: this.message.id,
            },
        });
    }

    get imStatusClassName() {
        let res = "position-absolute bottom-0 end-0";
        if (this.hasOpenChatFeature) {
            res += " cursor-pointer";
        }
        return res;
    }

    /**
     * Modifies the message to add the 'read more/read less' functionality
     * All element nodes with 'data-o-mail-quote' attribute are concerned.
     * All text nodes after a ``#stopSpelling`` element are concerned.
     * Those text nodes need to be wrapped in a span (toggle functionality).
     * All consecutive elements are joined in one 'read more/read less'.
     *
     * FIXME This method should be rewritten (task-2308951)
     *
     * @param {jQuery} $element
     */
    insertReadMoreLess($element) {
        const groups = [];
        let readMoreNodes;

        // nodeType 1: element_node
        // nodeType 3: text_node
        const $children = $element
            .contents()
            .filter(
                (index, content) =>
                    content.nodeType === 1 || (content.nodeType === 3 && content.nodeValue.trim())
            );

        for (const child of $children) {
            let $child = $(child);

            // Hide Text nodes if "stopSpelling"
            if (child.nodeType === 3 && $child.prevAll('[id*="stopSpelling"]').length > 0) {
                // Convert Text nodes to Element nodes
                $child = $("<span>", {
                    text: child.textContent,
                    "data-o-mail-quote": "1",
                });
                child.parentNode.replaceChild($child[0], child);
            }

            // Create array for each 'read more' with nodes to toggle
            if (
                $child.attr("data-o-mail-quote") ||
                ($child.get(0).nodeName === "BR" &&
                    $child.prev('[data-o-mail-quote="1"]').length > 0)
            ) {
                if (!readMoreNodes) {
                    readMoreNodes = [];
                    groups.push(readMoreNodes);
                }
                $child.hide();
                readMoreNodes.push($child);
            } else {
                readMoreNodes = undefined;
                this.insertReadMoreLess($child);
            }
        }

        for (const group of groups) {
            const index = this.state.lastReadMoreIndex++;
            // Insert link just before the first node
            const $readMoreLess = $("<a>", {
                class: "o-mail-read-more-less d-block",
                href: "#",
                text: "Read More",
            }).insertBefore(group[0]);

            // Toggle All next nodes
            if (!this.state.isReadMoreByIndex.has(index)) {
                this.state.isReadMoreByIndex.set(index, true);
            }
            const updateFromState = () => {
                const isReadMore = this.state.isReadMoreByIndex.get(index);
                for (const $child of group) {
                    $child.hide();
                    $child.toggle(!isReadMore);
                }
                $readMoreLess.text(isReadMore ? "Read More" : "Read Less");
            };
            $readMoreLess.click((e) => {
                e.preventDefault();
                this.state.isReadMoreByIndex.set(index, !this.state.isReadMoreByIndex.get(index));
                updateFromState();
            });
            updateFromState();
        }
    }

    openReactionMenu() {
        this.dialog.add(MessageReactionMenu, {
            message: this.props.message,
        });
    }
}
