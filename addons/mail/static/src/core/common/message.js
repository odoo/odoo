import { AttachmentList } from "@mail/core/common/attachment_list";
import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";
import { MessageInReply } from "@mail/core/common/message_in_reply";
import { MessageLinkPreviewList } from "@mail/core/common/message_link_preview_list";
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
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { createElementWithContent } from "@web/core/utils/html";
import { getOrigin, url } from "@web/core/utils/urls";
import { useMessageActions } from "./message_actions";
import { cookie } from "@web/core/browser/cookie";
import { rpc } from "@web/core/network/rpc";
import { discussComponentRegistry } from "./discuss_component_registry";
import { NotificationMessage } from "./notification_message";
import { useLongPress } from "@mail/utils/common/hooks";
import { ActionList } from "./action_list";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";

/**
 * @typedef {Object} Props
 * @property {boolean} [hasActions=true]
 * @property {boolean} [highlighted]
 * @property {function} [onParentMessageClick]
 * @property {import("models").Message} message
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
        ActionList,
        ActionSwiper,
        AttachmentList,
        Composer,
        Dropdown,
        ImStatus,
        MessageInReply,
        MessageLinkPreviewList,
        MessageReactions,
        Popover: MessageNotificationPopover,
        RelativeTime,
        NotificationMessage,
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
        "previousMessage?",
        "squashed?",
        "thread?",
        "messageSearch?",
        "className?",
        "showDates?",
        "isFirstMessage?",
        "isReadOnly?",
    ];
    static template = "mail.Message";

    setup() {
        super.setup();
        this.popover = usePopover(this.constructor.components.Popover, { position: "top" });
        this.state = useState({
            isHovered: false,
            isClicked: false,
            expandOptions: false,
            emailHeaderOpen: false,
            showTranslation: false,
        });
        /** @type {ShadowRoot} */
        this.shadowRoot;
        this.root = useRef("root");
        if (isMobileOS()) {
            useLongPress("root", {
                action: () => this.openMobileActions(),
                predicate: () => !this.isEditing,
            });
        }
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
        this.fileViewer = useFileViewer();
        useChildSubEnv({
            message: this.props.message,
            alignedRight: this.isAlignedRight,
        });
        onMounted(() => {
            if (this.shadowBody.el) {
                this.shadowRoot = this.shadowBody.el.attachShadow({ mode: "open" });
                const color = cookie.get("color_scheme") === "dark" ? "white" : "black";
                const shadowStyle = document.createElement("style");
                shadowStyle.textContent = `
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
                const ellipsisStyle = document.createElement("style");
                ellipsisStyle.textContent = `
                    .o-mail-ellipsis {
                        min-width: 2.7ch;
                        background-color: ButtonFace;
                        border-radius: 50rem;
                        border: 0;
                        display: block
                        font: -moz-button;
                        font-size: .75rem;
                        font-weight: 500;
                        line-height: 1.1;
                        cursor: pointer;
                        padding: 0 4px;
                        vertical-align: top;
                        color #ffffff;
                        text-decoration: none;
                        text-align: center;
                        &:hover {
                            background-color: -moz-buttonhoverface;
                        }
                    }
                `;
                this.shadowRoot.appendChild(ellipsisStyle);
            }
        });
        useEffect(
            () => {
                if (this.shadowBody.el) {
                    const bodyEl = createElementWithContent(
                        "span",
                        this.state.showTranslation
                            ? this.message.richTranslationValue
                            : this.props.messageSearch?.highlight(this.message.richBody) ??
                                  this.message.richBody
                    );
                    this.prepareMessageBody(bodyEl);
                    this.shadowRoot.appendChild(bodyEl);
                    return () => {
                        this.shadowRoot.removeChild(bodyEl);
                    };
                }
            },
            () => [
                this.state.showTranslation,
                this.message.richTranslationValue,
                this.props.messageSearch?.searchTerm,
                this.message.richBody,
                this.isEditing,
            ]
        );
        useEffect(
            () => {
                if (!this.isEditing) {
                    this.prepareMessageBody(this.messageBody.el);
                }
            },
            () => [this.isEditing, this.message.richBody]
        );
    }

    get attClass() {
        return {
            "user-select-none": isMobileOS(),
            [this.props.className]: true,
            "o-card p-2 ps-1 mx-1 mt-1 mb-1 border border-dark shadow-sm rounded-3":
                this.props.asCard,
            "pt-1": !this.props.asCard && !this.props.squashed,
            "o-pt-0_5": !this.props.asCard && this.props.squashed,
            "o-selfAuthored": this.message.isSelfAuthored && !this.env.messageCard,
            "o-selected": this.props.thread?.composer.replyToMessage?.eq(this.props.message),
            "o-squashed": this.props.squashed,
            "mt-1":
                !this.props.squashed &&
                this.props.thread &&
                !this.env.messageCard &&
                !this.props.asCard,
            "px-1": this.props.isInChatWindow,
            "opacity-50": this.props.thread?.composer.replyToMessage?.notEq(this.props.message),
            "o-actionMenuMobileOpen": this.ui.isSmall && this.optionsDropdown.isOpen,
            "o-editing": this.isEditing,
        };
    }

    get authorAvatarAttClass() {
        return {
            "object-fit-contain": this.props.message.author_id?.is_company,
            "object-fit-cover": !this.props.message.author_id?.is_company,
        };
    }

    get authorAvatarUrl() {
        if (
            this.message.message_type &&
            this.message.message_type.includes("email") &&
            !this.message.author_id &&
            !this.message.author_guest_id
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

    get isEditing() {
        return !this.props.isReadOnly && this.props.message.composer;
    }

    get message() {
        return this.props.message;
    }

    /** Max amount of quick actions, including "..." */
    get quickActionCount() {
        return this.env.inChatWindow ? 2 : 4;
    }

    get showSubtypeDescription() {
        return (
            this.message.subtype_id?.description &&
            this.message.subtype_id.description.toLowerCase() !==
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
            !this.props.message.isDiscussion &&
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
        return (
            !this.message.is_transient &&
            !this.message.isPending &&
            this.message.thread &&
            this.message.thread.notEq(this.props.thread)
        );
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
        const img = ev.target.closest('.o_mail_activity_note_content img');
        if (img) {
            ev.stopPropagation();
            const imgName = img.src ? decodeURIComponent(img.src.split('/').pop().split('?')[0]) : '';
            const fileModel = {
                isImage: true,
                isViewable: true,
                name: imgName,
                defaultSource: img.src,
                downloadUrl: img.src,
            };
        this.fileViewer.open(fileModel);
    }
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

    /** @param {HTMLElement} bodyEl */
    prepareMessageBody(bodyEl) {
        if (!bodyEl) {
            return;
        }
        const editedEl = bodyEl.querySelector(".o-mail-Message-edited");
        editedEl?.replaceChildren(renderToElement("mail.Message.edited"));
        for (const linkEl of bodyEl.querySelectorAll(".o_channel_redirect")) {
            const text = linkEl.textContent.substring(1); // remove '#' prefix
            const icon = linkEl.classList.contains("o_channel_redirect_asThread")
                ? "fa fa-comments-o"
                : "fa fa-hashtag";
            const iconEl = renderToElement("mail.Message.mentionedChannelIcon", { icon });
            linkEl.replaceChildren(iconEl);
            linkEl.insertAdjacentText("beforeend", ` ${text}`);
        }
        for (const el of bodyEl.querySelectorAll(".o_message_redirect")) {
            // only transform links targetting the same database
            if (el.getAttribute("href")?.startsWith(getOrigin())) {
                const message = this.store["mail.message"].get(el.dataset.oeId);
                if (message?.thread?.displayName) {
                    el.classList.add("o_message_redirect_transformed");
                    el.replaceChildren(renderToElement("mail.Message.messageLink", { message }));
                }
            }
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
        this.message.exitEditMode(this.props.thread);
    }

    onClickNotification(ev) {
        const message = toRaw(this.message);
        if (message.failureNotifications.length > 0) {
            markEventHandled(ev, "Message.ClickFailure");
        }
        this.popover.open(ev.target, { message });
    }

    /** @param {MouseEvent} [ev] */
    openMobileActions(ev) {
        if (!isMobileOS()) {
            return;
        }
        ev?.stopPropagation();
        this.optionsDropdown.open();
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
