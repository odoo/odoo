// @ts-check
/** @odoo-module native */
import { ActionList } from "@mail/core/common/action_list";
import { AttachmentList } from "@mail/core/common/attachment_list";
import { Composer } from "@mail/core/common/composer";
import { ImStatus } from "@mail/core/common/im_status";
import { MessageInReply } from "@mail/core/common/message_in_reply";
import { MessageLinkPreviewList } from "@mail/core/common/message_link_preview_list";
import { MessageNotificationPopover } from "@mail/core/common/message_notification_popover";
import { handleValidChannelMention } from "@mail/core/common/message_post";
import { MessageReactionMenu } from "@mail/core/common/message_reaction_menu";
import { MessageReactions } from "@mail/core/common/message_reactions";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { useLongPress, useRegisterMessageRef } from "@mail/utils/common/hooks";
import { loadCssFromBundle } from "@mail/utils/common/misc";
import {
    Component,
    onWillRender,
    status,
    toRaw,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { ActionSwiper } from "@web/components/action_swiper";
import { Dropdown, useDropdownState } from "@web/components/dropdown";
import { hasTouch, isMobileOS } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { _t } from "@web/core/translation";
import { isEventHandled, markEventHandled } from "@web/core/utils/dom/events";
import { createElementWithContent } from "@web/core/utils/dom/html";
import { attachShadowRoot } from "@web/core/utils/dom/ui";
import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { getOrigin, url } from "@web/core/utils/urls";
import { rootIdOf } from "@web/ui/overlay/root_id";
import { usePopover } from "@web/ui/popover";

import { discussComponentRegistry } from "./discuss_component_registry.js";
import { useMessageActions } from "./message_actions.js";
import { NotificationMessage } from "./notification_message.js";

class MessageDropdown extends Dropdown {
    get isBottomSheet() {
        return hasTouch() && this.props.bottomSheet;
    }
}

const log = makeLogger("mail.message.ui");

/**
 * @typedef {Object} Props
 * @property {boolean} [hasActions=true]
 * @property {boolean} [highlighted]
 * @property {function} [onParentMessageClick]
 * @property {import("models").Message} message
 * @property {boolean} [squashed]
 * @property {import("models").Thread} [thread]
 * @property {ReturnType<import('@mail/core/common/message_search_hook').useMessageSearch>} [messageSearch]
 * @property {string} [className]
 * @property {boolean} [asCard]
 * @property {( message: import("models").Message, ref: import("@odoo/owl").Ref|null, ) => void} [registerMessageRef]
 * @property {boolean} [isInChatWindow=false]
 * @property {import("models").Message} [previousMessage]
 * @property {boolean} [showDates]
 * @property {boolean} [isReadOnly]
 * @extends {Component<Props, import("@web/env").OdooEnv>}
 */
export class Message extends Component {
    static SHADOW_LINK_COLOR = "#017e84";
    static SHADOW_HIGHLIGHT_COLOR = "#e99d00bf";
    static SHADOW_LINK_HOVER_COLOR = "#016b70";
    static components = {
        ActionList,
        ActionSwiper,
        AttachmentList,
        Composer,
        Dropdown: MessageDropdown,
        ImStatus,
        MessageInReply,
        MessageLinkPreviewList,
        MessageReactions,
        Popover: MessageNotificationPopover,
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
        "isReadOnly?",
    ];
    static template = "mail.Message";
    /** @type {{body: string | import("@odoo/owl").Markup, description: string, result: boolean}|undefined} */
    subtypeDescriptionCache;

    _setupServicesAndRefs() {
        this.store = useService("mail.store");
        this.linkNavigation = useService("mail.link_navigation");
        this.popover = usePopover(
            /** @type {typeof Message} */ (this.constructor).components.Popover,
            {
                position: "top",
            },
        );
        this.state = useState({
            isHovered: false,
            isClicked: false,
            expandOptions: false,
            emailHeaderOpen: false,
        });
        /** @type {ShadowRoot} */
        this.shadowRoot;
        this.root = useRegisterMessageRef();
        if (isMobileOS()) {
            useLongPress("root", {
                action: () => this.openMobileActions(),
                predicate: () => !this.isEditing,
            });
        }
        this.hasTouch = hasTouch;
        this.messageBody = useRef("body");
        this.messageActions = useMessageActions({
            message: () => this.message,
            thread: () => this.props.thread,
        });
        onWillRender(() => this.computeActions());
        this.shadowBody = useRef("shadowBody");
        this.dialog = useService("dialog");
        this.ui = useService("ui");
        this.openReactionMenu = this.openReactionMenu.bind(this);
        this.optionsDropdown = useDropdownState();
        useSubEnv({ inMessage: true });
        useChildSubEnv({
            message: this.props.message,
            alignedRight: this.isAlignedRight,
        });
    }
    _setupMessageEffects() {
        useEffect(
            () => {
                const el = this.shadowBody.el;
                if (el) {
                    if (!this.shadowRoot || this.shadowRoot.host !== el) {
                        log.lifecycle("shadow body attached", () => ({
                            messageId: this.message.id,
                            reused: Boolean(el.shadowRoot),
                        }));
                        if (el.shadowRoot) {
                            this.shadowRoot = el.shadowRoot;
                        } else {
                            this.shadowRoot = attachShadowRoot(el);
                            this.setupShadowStyles(this.shadowRoot);
                        }
                    }
                    const shadowRoot = this.shadowRoot;
                    const endShadowBody = log.perf("shadow body render");
                    const bodyEl = createElementWithContent(
                        "span",
                        this.message.showTranslation
                            ? this.message.richTranslationValue
                            : (this.props.messageSearch?.highlight(
                                  this.message.richBody,
                              ) ?? this.message.richBody),
                    );
                    this.prepareMessageBody(bodyEl);
                    shadowRoot.appendChild(bodyEl);
                    endShadowBody({ messageId: this.message.id });
                    return () => {
                        shadowRoot.removeChild(bodyEl);
                    };
                }
            },
            () => [
                this.shadowBody.el,
                this.message.showTranslation,
                this.message.richTranslationValue,
                this.props.messageSearch?.searchTerm,
                this.message.richBody,
                this.isEditing,
            ],
        );
        useEffect(
            () => {
                if (!this.isEditing) {
                    this.prepareMessageBody(this.messageBody.el);
                }
            },
            () => [
                this.isEditing,
                this.message.richBody,
                this.props.messageSearch?.searchTerm,
                this.message.showTranslation,
                this.message.richTranslationValue,
            ],
        );
    }
    setup() {
        useLifecycleLog(log);
        super.setup();
        this._setupServicesAndRefs();
        this._setupMessageEffects();
    }

    /** @param {ShadowRoot} shadowRoot */
    setupShadowStyles(shadowRoot) {
        const color = this.store.isOdooWhiteTheme ? "dark" : "white";
        loadCssFromBundle(shadowRoot, "mail.assets_message_email");
        const shadowStyle = document.createElement("style");
        shadowStyle.textContent = `
            * {
                background-color: transparent !important;
                color: ${color} !important;
            }
            a, a * {
                color: ${/** @type {typeof Message} */ (this.constructor).SHADOW_LINK_COLOR} !important;
            }
            a:hover, a *:hover {
                color: ${/** @type {typeof Message} */ (this.constructor).SHADOW_LINK_HOVER_COLOR} !important;
            }
            .o-mail-Message-searchHighlight {
                background: ${/** @type {typeof Message} */ (this.constructor).SHADOW_HIGHLIGHT_COLOR} !important;
            }
        `;
        if (!this.store.isOdooWhiteTheme) {
            shadowRoot.appendChild(shadowStyle);
        }
        const ellipsisStyle = document.createElement("style");
        ellipsisStyle.textContent = `
            .o-mail-ellipsis {
                min-width: 2.7ch;
                background-color: ButtonFace;
                border-radius: 50rem;
                border: 0;
                display: block;
                font: -moz-button;
                font-size: .75rem;
                font-weight: 500;
                line-height: 1.1;
                cursor: pointer;
                padding: 0 4px;
                vertical-align: top;
                color: #ffffff;
                text-decoration: none;
                text-align: center;
                &:hover {
                    background-color: -moz-buttonhoverface;
                }
            }
        `;
        shadowRoot.appendChild(ellipsisStyle);
    }

    computeActions() {
        const allActions = this.messageActions.actions;
        const previousActions = this.lastComputedActions;
        if (
            previousActions &&
            previousActions.length === allActions.length &&
            previousActions.every((action, index) => action === allActions[index])
        ) {
            return;
        }
        this.lastComputedActions = allActions;
        const quickActions = allActions.slice(
            0,
            allActions.length > this.quickActionCount
                ? this.quickActionCount - 1
                : this.quickActionCount,
        );
        const moreActions =
            allActions.length > this.quickActionCount
                ? allActions.slice(this.quickActionCount - 1)
                : [];
        const moreAction = moreActions.length
            ? this.messageActions.more({
                  actions: moreActions,
                  dropdownMenuClass: "o-mail-Message-moreMenu",
                  dropdownPosition: this.isAlignedRight
                      ? this.message.threadAsNewest
                          ? "left-end"
                          : "left-start"
                      : this.message.threadAsNewest
                        ? "right-end"
                        : "right-start",
                  name: this.expandText,
              })
            : undefined;
        const actions = moreAction ? [...quickActions, moreAction] : quickActions;
        if (this.isAlignedRight) {
            actions.reverse();
        }
        this.moreAction = moreAction;
        this.quickActions = quickActions;
        this.actions = actions;
    }

    get attClass() {
        return {
            "user-select-none o-isMobileOS": isMobileOS(),
            [this.props.className]: true,
            "o-card p-2 ps-1 mx-1 mt-1 mb-1 border border-dark rounded-2":
                this.props.asCard,
            "pt-1": !this.props.asCard && !this.props.squashed,
            "o-pt-0_5": !this.props.asCard && this.props.squashed,
            "o-selfAuthored": this.message.isSelfAuthored && !this.env.messageCard,
            "o-selected": this.props.message.composerAsReplyToMessage?.thread.eq(
                this.props.thread,
            ),
            "o-squashed": this.props.squashed,
            "mt-1":
                !this.props.squashed &&
                this.props.thread &&
                !this.env.messageCard &&
                !this.props.asCard,
            "px-1": this.props.isInChatWindow,
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

    get quickActionCount() {
        if (isMobileOS()) {
            return 1;
        }
        return this.env.inChatWindow || this.env.inMeetingChat ? 2 : 4;
    }

    get showSubtypeDescription() {
        const description = this.message.subtype_id?.description;
        if (!description) {
            return description;
        }
        const body = this.message.body || "";
        let cache = this.subtypeDescriptionCache;
        if (cache?.description !== description || cache.body !== body) {
            cache = {
                body,
                description,
                result:
                    description.toLowerCase() !==
                    htmlToTextContentInline(body).toLowerCase(),
            };
            this.subtypeDescriptionCache = cache;
        }
        return cache.result;
    }

    get messageTypeText() {
        if (this.props.message.message_type === "notification") {
            return _t("System notification");
        }
        if (this.props.message.message_type === "auto_comment") {
            return _t("Automated message");
        }
        if (this.props.message.message_type === "out_of_office") {
            return _t("Out-of-office message");
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
            this.reactionPicker?.isOpen ||
            Boolean(this.moreAction?.isActive)
        );
    }

    get isAlignedRight() {
        return Boolean(this.env.inChatWindow && this.props.message.isSelfAuthored);
    }

    get isMobileOS() {
        return isMobileOS();
    }

    get isPersistentMessageFromAnotherThread() {
        return Boolean(
            this.message.persistent && this.message.thread?.notEq(this.props.thread),
        );
    }

    get translatedFromText() {
        return _t("(Translated from: %(language)s)", {
            language: this.message.translationSource,
        });
    }

    get translationFailureText() {
        return _t("(Translation Failure: %(error)s)", {
            error: this.message.translationErrors,
        });
    }

    onMouseenter() {
        this.state.isHovered = true;
    }

    onMouseleave() {
        this.state.isHovered = false;
        this.state.isClicked = false;
    }

    /** @returns {boolean} */
    get shouldDisplayAuthorName() {
        if (!this.env.inChatWindow) {
            return true;
        }
        if (this.message.isSelfAuthored) {
            return false;
        }
        if (this.props.thread.isDirectChat) {
            return false;
        }
        return true;
    }

    /** @param {import("models").Attachment} attachment */
    async onClickAttachmentUnlink(attachment) {
        log.logic("onClickAttachmentUnlink", () => ({
            messageId: this.message.id,
            attachmentId: attachment.id,
        }));
        await toRaw(attachment).remove();
    }

    /** @param {MouseEvent} ev */
    async onClick(ev) {
        if (this.linkNavigation.handleClickOnLink(ev, this.props.thread)) {
            log.logic("onClick handled as link navigation", () => ({
                messageId: this.message.id,
            }));
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
                        if (status(this) !== "destroyed") {
                            this.state.isClicked = false;
                        }
                    },
                    { capture: true, once: true },
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
        const channelLinks = bodyEl.querySelectorAll("a.o_channel_redirect");
        handleValidChannelMention(Array.from(channelLinks));
        for (const el of bodyEl.querySelectorAll(".o_message_redirect")) {
            if (el.getAttribute("href")?.startsWith(getOrigin())) {
                const message = this.store["mail.message"].get(el.dataset.oeId);
                if (message?.thread?.displayName) {
                    el.classList.add("o_message_redirect_transformed");
                    el.replaceChildren(
                        renderToElement("mail.Message.messageLink", { message }),
                    );
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

    /** @param {MouseEvent} ev */
    onClickNotification(ev) {
        const message = toRaw(this.message);
        log.logic("onClickNotification", () => ({
            messageId: message.id,
            failures: message.failureNotifications.length,
        }));
        if (message.failureNotifications.length > 0) {
            markEventHandled(ev, "Message.ClickFailure");
        }
        this.popover.open(/** @type {HTMLElement} */ (ev.target), { message });
    }

    /** @param {MouseEvent} [ev] */
    openMobileActions(ev) {
        if (!isMobileOS()) {
            return;
        }
        ev?.stopPropagation();
        this.optionsDropdown.open();
    }

    /** @returns {string | undefined} */
    get overlayRootId() {
        return rootIdOf(this.root.el);
    }

    /** @param {import("models").MessageReactions} [reaction] */
    openReactionMenu(reaction) {
        const message = toRaw(this.props.message);
        log.logic("openReactionMenu", () => ({
            messageId: message.id,
            reaction: reaction?.content,
        }));
        this.dialog.add(
            MessageReactionMenu,
            { message, initialReaction: reaction },
            { rootId: this.overlayRootId },
        );
    }

    async onClickToggleTranslation() {
        toRaw(this.props.message).onClickToggleTranslation();
    }

    get shouldHideFromMessageListOnDelete() {
        return false;
    }
}

discussComponentRegistry.add("Message", Message);
