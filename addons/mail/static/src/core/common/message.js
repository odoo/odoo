import { AttachmentList } from "@mail/core/common/attachment_list";
import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";
import { LinkPreviewList } from "@mail/core/common/link_preview_list";
import { MessageInReply } from "@mail/core/common/message_in_reply";
import { MessageNotificationPopover } from "@mail/core/common/message_notification_popover";
import { MessageReactionMenu } from "@mail/core/common/message_reaction_menu";
import { MessageReactions } from "@mail/core/common/message_reactions";
import { RelativeTime } from "@mail/core/common/relative_time";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";
import { renderToElement } from "@web/core/utils/render";

import {
    Component,
    markup,
    onMounted,
    onPatched,
    onWillDestroy,
    onWillUpdateProps,
    toRaw,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { ActionSwiper } from "@web/core/action_swiper/action_swiper";
import { hasTouch, isMobileOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { messageActionsRegistry, useMessageActions } from "./message_actions";
import { cookie } from "@web/core/browser/cookie";
import { rpc } from "@web/core/network/rpc";
import { escape } from "@web/core/utils/strings";
import { MessageActionMenuMobile } from "./message_action_menu_mobile";
import { discussComponentRegistry } from "./discuss_component_registry";

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
        "asCard?",
        "registerMessageRef?",
        "hasActions?",
        "isInChatWindow?",
        "onParentMessageClick?",
        "message",
        "messageEdition?",
        "messageToReplyTo?",
        "previousMessage?",
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
        this.escape = escape;
        this.popover = usePopover(this.constructor.components.Popover, { position: "top" });
        this.state = useState({
            isEditing: false,
            isHovered: false,
            isClicked: false,
            expandOptions: false,
            emailHeaderOpen: false,
            showTranslation: false,
            actionMenuMobileOpen: false,
        });
        /** @type {ShadowRoot} */
        this.shadowRoot;
        this.root = useRef("root");
        onWillUpdateProps((nextProps) => {
            this.props.registerMessageRef?.(this.props.message, null);
        });
        onMounted(() => this.props.registerMessageRef?.(this.props.message, this.root));
        onPatched(() => this.props.registerMessageRef?.(this.props.message, this.root));
        onWillDestroy(() => this.props.registerMessageRef?.(this.props.message, null));
        this.hasTouch = hasTouch;
        this.messageBody = useRef("body");
        this.messageActions = useMessageActions();
        this.store = useService("mail.store");
        this.shadowBody = useRef("shadowBody");
        this.dialog = useService("dialog");
        this.ui = useService("ui");
        this.openReactionMenu = this.openReactionMenu.bind(this);
        this.optionsDropdown = useDropdownState();
        useChildSubEnv({
            message: this.props.message,
            alignedRight: this.isAlignedRight,
        });
        useEffect(
            (editingMessage) => {
                if (this.props.message.eq(editingMessage)) {
                    messageActionsRegistry.get("edit").onClick(this);
                }
            },
            () => [this.props.messageEdition?.editingMessage]
        );
        onMounted(() => {
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
                    const bodyEl = document.createElement("span");
                    bodyEl.innerHTML = this.state.showTranslation
                        ? this.message.translationValue
                        : this.props.messageSearch?.highlight(this.message.body) ??
                          this.message.body;
                    this.prepareMessageBody(bodyEl);
                    this.shadowRoot.appendChild(bodyEl);
                    return () => {
                        this.shadowRoot.removeChild(bodyEl);
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
        useEffect(
            () => {
                if (!this.state.isEditing) {
                    this.prepareMessageBody(this.messageBody.el);
                }
            },
            () => [this.state.isEditing, this.message.body]
        );
    }

    get attClass() {
        return {
            [this.props.className]: true,
            "o-card p-2 mt-2": this.props.asCard,
            "pt-1": !this.props.asCard,
            "o-selfAuthored": this.message.isSelfAuthored && !this.env.messageCard,
            "o-selected": this.props.messageToReplyTo?.isSelected(
                this.props.thread,
                this.props.message
            ),
            "o-squashed": this.props.squashed,
            "mt-1":
                !this.props.squashed &&
                this.props.thread &&
                !this.env.messageCard &&
                !this.props.asCard,
            "px-2": this.props.isInChatWindow,
            "opacity-50": this.props.messageToReplyTo?.isNotSelected(
                this.props.thread,
                this.props.message
            ),
            "o-actionMenuMobileOpen": this.state.actionMenuMobileOpen,
            "o-editing": this.state.isEditing,
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

    /** Max amount of quick actions, including "..." */
    get quickActionCount() {
        return this.env.inChatter ? 3 : this.env.inChatWindow ? 2 : 4;
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

    get isMobileOS() {
        return isMobileOS();
    }

    get isPersistentMessageFromAnotherThread() {
        return !this.isOriginThread && !this.message.is_transient && this.message.thread;
    }

    get isOriginThread() {
        if (!this.props.thread) {
            return false;
        }
        return this.props.thread.eq(this.message.thread);
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

    async onClickAttachmentUnlink(attachment) {
        await toRaw(attachment).remove();
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClick(ev) {
        if (this.store.handleClickOnLink(ev, this.props.thread)) {
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

    /**
     * @param {MouseEvent} ev
     */
    async onClickNotificationMessage(ev) {
        this.store.handleClickOnLink(ev, this.props.thread);
        const { oeType, oeId } = ev.target.dataset;
        if (oeType === "highlight") {
            await this.env.messageHighlight?.highlightMessage(
                this.store["mail.message"].insert({
                    id: Number(oeId),
                    res_id: this.props.thread.id,
                    model: this.props.thread.model,
                    thread: this.props.thread,
                }),
                this.props.thread
            );
        }
    }

    /** @param {HTMLElement} bodyEl */
    prepareMessageBody(bodyEl) {
        if (!bodyEl) {
            return;
        }
        const linkEls = bodyEl.querySelectorAll(".o_channel_redirect");
        for (const linkEl of linkEls) {
            const text = linkEl.textContent.substring(1); // remove '#' prefix
            const icon = linkEl.classList.contains("o_channel_redirect_asThread")
                ? "fa fa-comments-o"
                : "fa fa-hashtag";
            const iconEl = renderToElement("mail.Message.mentionedChannelIcon", { icon });
            linkEl.replaceChildren(iconEl);
            linkEl.insertAdjacentText("beforeend", ` ${text}`);
        }
    }

    getAuthorAttClass() {
        return { "opacity-50": this.message.isPending };
    }

    getAvatarContainerAttClass() {
        return {
            "opacity-50": this.message.isPending,
            "o-inChatWindow": this.env.inChatWindow,
        };
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

    /** @param {MouseEvent} [ev] */
    openMobileActions(ev) {
        if (!isMobileOS()) {
            return;
        }
        ev?.stopPropagation();
        this.state.actionMenuMobileOpen = true;
        this.dialog.add(
            MessageActionMenuMobile,
            {
                message: this.props.message,
                thread: this.props.thread,
                isFirstMessage: this.props.isFirstMessage,
                messageToReplyTo: this.props.messageToReplyTo,
                openReactionMenu: () => this.openReactionMenu(),
                state: this.state,
            },
            { context: this, onClose: () => (this.state.actionMenuMobileOpen = false) }
        );
    }

    openReactionMenu(reaction) {
        const message = toRaw(this.props.message);
        this.dialog.add(
            MessageReactionMenu,
            { message, initialReaction: reaction },
            { context: this }
        );
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

discussComponentRegistry.add("Message", Message);
