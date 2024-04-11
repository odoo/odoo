import { AttachmentList } from "@mail/core/common/attachment_list";
import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";
import { LinkPreviewList } from "@mail/core/common/link_preview_list";
import { MessageConfirmDialog } from "@mail/core/common/message_confirm_dialog";
import { MessageInReply } from "@mail/core/common/message_in_reply";
import { MessageNotificationPopover } from "@mail/core/common/message_notification_popover";
import { MessageReactionMenu } from "@mail/core/common/message_reaction_menu";
import { MessageReactions } from "@mail/core/common/message_reactions";
import { MessageSeenIndicator } from "@mail/core/common/message_seen_indicator";
import { RelativeTime } from "@mail/core/common/relative_time";
import { convertBrToLineBreak, htmlToTextContentInline } from "@mail/utils/common/format";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";

import {
    Component,
    markup,
    onMounted,
    toRaw,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { ActionSwiper } from "@web/core/action_swiper/action_swiper";
import { hasTouch } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { useMessageActions } from "./message_actions";
import { cookie } from "@web/core/browser/cookie";
import { rpcWithEnv } from "@mail/utils/common/misc";

/**
 * @typedef {Object} Props
 * @property {boolean} [hasActions=true]
 * @property {boolean} [highlighted]
 * @property {function} [onParentMessageClick]
 * @property {import("models").Message} message
 * @property {import("@mail/utils/common/hooks").MessageToReplyTo} [messageToReplyTo]
 * @property {boolean} [squashed]
 * @property {import("models").Thread} [thread]
 * @property {ReturnType<import('@mail/core/common/message_search_hook').useMessageSearch>} [messageSearch]
 * @property {String} [className]
 * @extends {Component<Props, Env>}
 */
export class Message extends Component {
    // This is the darken version of #71639e
    static SHADOW_LINK_COLOR = "#66598f";
    static SHADOW_HIGHLIGHT_COLOR = "#e99d00bf";
    static SHADOW_LINK_HOVER_COLOR = "#564b79";
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
        showDates: true,
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
        "messageSearch?",
        "className?",
        "showDates?",
        "isFirstMessage?",
    ];
    static template = "mail.Message";

    setup() {
        super.setup();
        rpc = rpcWithEnv(this.env);
        this.popover = usePopover(this.constructor.components.Popover, { position: "top" });
        this.state = useState({
            isEditing: false,
            isHovered: false,
            isClicked: false,
            expandOptions: false,
            emailHeaderOpen: false,
            showTranslation: false,
        });
        /** @type {ShadowRoot} */
        this.shadowRoot;
        this.root = useRef("root");
        this.hasTouch = hasTouch;
        this.messageBody = useRef("body");
        this.messageActions = useMessageActions();
        this.store = useState(useService("mail.store"));
        this.shadowBody = useRef("shadowBody");
        this.dialog = useService("dialog");
        this.ui = useState(useService("ui"));
        this.openReactionMenu = this.openReactionMenu.bind(this);
        this.optionsDropdown = useDropdownState();
        useChildSubEnv({
            message: this.props.message,
            alignedRight: this.isAlignedRight,
        });
        useEffect(
            (editingMessage) => {
                if (this.props.message.eq(editingMessage)) {
                    this.enterEditMode();
                }
            },
            () => [this.props.messageEdition?.editingMessage]
        );
        useEffect(
            (highlighted) => {
                if (highlighted) {
                    this.root.el.scrollIntoView({ behavior: "smooth", block: "center" });
                }
            },
            () => [this.props.highlighted]
        );
        onMounted(() => {
            if (this.messageBody.el) {
                this.prepareMessageBody(this.messageBody.el);
            }
            if (this.shadowBody.el) {
                this.shadowRoot = this.shadowBody.el.attachShadow({ mode: "open" });
                const color = cookie.get("color_scheme") === "dark" ? "white" : "black";
                const shadowStyle = document.createElement("style");
                shadowStyle.innerHTML = `
                    * {
                        background-color: transparent !important;
                        color: ${color} !important;
                    }
                    a, a * {
                        color: ${this.constructor.SHADOW_LINK_COLOR} !important;
                    }
                    a:hover, a *:hover {
                        color: ${this.constructor.SHADOW_LINK_HOVER_COLOR} !important;
                    }
                    .o-mail-Message-searchHighlight {
                        background: ${this.constructor.SHADOW_HIGHLIGHT_COLOR} !important;
                    }
                `;
                if (cookie.get("color_scheme") === "dark") {
                    this.shadowRoot.appendChild(shadowStyle);
                }
            }
        });
        useEffect(
            () => {
                if (this.shadowBody.el) {
                    const body = document.createElement("span");
                    body.innerHTML = this.state.showTranslation
                        ? this.message.translationValue
                        : this.props.messageSearch?.highlight(this.message.body) ??
                          this.message.body;
                    this.prepareMessageBody(body);
                    this.shadowRoot.appendChild(body);
                    return () => {
                        this.shadowRoot.removeChild(body);
                    };
                }
            },
            () => [
                this.state.showTranslation,
                this.message.translationValue,
                this.props.messageSearch?.searchTerm,
                this.message.body,
            ]
        );
    }

    get attClass() {
        return {
            [this.props.className]: true,
            "o-highlighted bg-view shadow-lg": this.props.highlighted,
            "o-selfAuthored": this.message.isSelfAuthored && !this.env.messageCard,
            "o-selected": this.props.messageToReplyTo?.isSelected(
                this.props.thread,
                this.props.message
            ),
            "o-squashed pb-1": this.props.squashed,
            "py-1": !this.props.squashed,
            "mt-2": !this.props.squashed && this.props.thread && !this.env.messageCard,
            "px-2": this.props.isInChatWindow,
            "opacity-50": this.props.messageToReplyTo?.isNotSelected(
                this.props.thread,
                this.props.message
            ),
        };
    }

    get authorAvatarAttClass() {
        return {
            o_object_fit_contain: this.props.message.author?.is_company,
            o_object_fit_cover: !this.props.message.author?.is_company,
        };
    }

    get authorName() {
        if (this.message.author) {
            return this.message.author.name;
        }
        return this.message.email_from;
    }

    get authorAvatarUrl() {
        if (
            this.message.message_type &&
            this.message.message_type.includes("email") &&
            !["partner", "guest"].includes(this.message.author?.type)
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }

        if (this.message.author) {
            return this.message.author.avatarUrl;
        }

        return this.store.DEFAULT_AVATAR;
    }

    get expandText() {
        return _t("Expand");
    }

    get message() {
        return this.props.message;
    }

    get quickActionCount() {
        return this.env.inChatter ? 2 : 3;
    }

    get showSubtypeDescription() {
        return (
            this.message.subtype_description &&
            this.message.subtype_description.toLowerCase() !==
                htmlToTextContentInline(this.message.body || "").toLowerCase()
        );
    }

    get messageTypeText() {
        if (this.props.message.message_type === "notification") {
            return _t("System notification");
        }
        if (this.props.message.message_type === "auto_comment") {
            return _t("Automated message");
        }
        if (
            !this.props.message.is_discussion &&
            this.props.message.message_type !== "user_notification"
        ) {
            return _t("Note");
        }
        return _t("Message");
    }

    get canAddReaction() {
        return Boolean(!this.message.is_transient && this.message.thread);
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
        return this.props.messageToReplyTo;
    }

    get canToggleStar() {
        return Boolean(
            !this.message.is_transient && this.message.thread && this.store.self.type === "partner"
        );
    }

    get showUnfollow() {
        return Boolean(
            this.message.thread?.selfFollower && this.props.thread?.model === "mail.box"
        );
    }

    get isActive() {
        return (
            this.state.isHovered ||
            this.state.isClicked ||
            this.emojiPicker?.isOpen ||
            this.optionsDropdown.isOpen
        );
    }

    get isAlignedRight() {
        return Boolean(this.env.inChatWindow && this.props.message.isSelfAuthored);
    }

    get isOriginThread() {
        if (!this.props.thread) {
            return false;
        }
        return this.props.thread.eq(this.message.thread);
    }

    get isInInbox() {
        if (!this.props.thread) {
            return false;
        }
        return this.props.thread.id === "inbox";
    }

    get translatable() {
        return this.store.hasMessageTranslationFeature && this.env.inChatter;
    }

    get translatedFromText() {
        return _t("(Translated from: %(language)s)", { language: this.message.translationSource });
    }

    get translationFailureText() {
        return _t("(Translation Failure: %(error)s)", { error: this.message.translationErrors });
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
        if (!this.env.inChatWindow) {
            return true;
        }
        if (this.message.isSelfAuthored) {
            return false;
        }
        if (this.props.thread.channel_type === "chat") {
            return false;
        }
        return true;
    }

    onClickDelete() {
        const message = toRaw(this.message);
        this.dialog.add(
            MessageConfirmDialog,
            {
                message,
                messageComponent: Message,
                prompt: _t("Are you sure you want to delete this message?"),
                onConfirm: () => message.remove(),
            },
            { context: this }
        );
    }

    onClickReplyTo(ev) {
        const message = toRaw(this.props.message);
        const thread = toRaw(this.props.thread);
        this.props.messageToReplyTo.toggle(thread, message);
    }

    async onClickAttachmentUnlink(attachment) {
        await toRaw(attachment).remove();
    }

    onClickMarkAsUnread() {
        const message = toRaw(this.message);
        const thread = toRaw(this.props.thread);
        const previousMessage = message.thread.getPreviousMessage(message);
        if (
            !thread.selfMember ||
            (!thread.selfMember.seen_message_id && !previousMessage) ||
            thread.selfMember.seen_message_id?.eq(previousMessage)
        ) {
            return;
        }
        return rpc("/discuss/channel/set_last_seen_message", {
            channel_id: message.thread.id,
            last_message_id: previousMessage ? previousMessage.id : false,
            allow_older: true,
        });
    }

    /**
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        const model = ev.target.dataset.oeModel;
        const id = Number(ev.target.dataset.oeId);
        const store = toRaw(this.store);
        if (ev.target.closest(".o_channel_redirect")) {
            ev.preventDefault();
            const thread = store.Thread.insert({ model, id });
            thread.open();
            return;
        }
        if (ev.target.closest(".o_mail_redirect")) {
            ev.preventDefault();
            const partnerId = Number(ev.target.dataset.oeId);
            if (user.partnerId !== partnerId) {
                this.store.openChat({ partnerId });
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

    /**
     * @param {HTMLElement} element
     */
    prepareMessageBody(element) {}

    enterEditMode() {
        const message = toRaw(this.props.message);
        const text = convertBrToLineBreak(message.body);
        message.composer = {
            mentionedPartners: message.recipients,
            text,
            selection: {
                start: text.length,
                end: text.length,
                direction: "none",
            },
        };
        this.state.isEditing = true;
    }

    exitEditMode() {
        const message = toRaw(this.props.message);
        this.props.messageEdition?.exitEditMode();
        message.composer = undefined;
        this.state.isEditing = false;
    }

    onClickNotification(ev) {
        const message = toRaw(this.message);
        if (message.failureNotifications.length > 0) {
            this.onClickFailure(ev);
        } else {
            this.popover.open(ev.target, { message });
        }
    }

    onClickFailure(ev) {
        const message = toRaw(this.message);
        markEventHandled(ev, "Message.ClickFailure");
        this.env.services.action.doAction("mail.mail_resend_message_action", {
            additionalContext: {
                mail_message_to_resend: message.id,
            },
        });
    }

    openReactionMenu() {
        const message = toRaw(this.props.message);
        this.dialog.add(MessageReactionMenu, { message }, { context: this });
    }

    async onClickToggleTranslation() {
        const message = toRaw(this.message);
        if (!message.translationValue) {
            const { error, lang_name, body } = await rpc("/mail/message/translate", {
                message_id: message.id,
            });
            message.translationValue = body && markup(body);
            message.translationSource = lang_name;
            message.translationErrors = error;
        }
        this.state.showTranslation =
            !this.state.showTranslation && Boolean(message.translationValue);
    }
}
