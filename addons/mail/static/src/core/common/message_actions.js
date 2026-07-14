import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { Action, ACTION_TAGS, useAction, UseActions } from "@mail/core/common/action";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";
import { MessageReactionMenu } from "@mail/core/common/message_reaction_menu";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { rpc } from "@web/core/network/rpc";

const { DateTime } = luxon;

export const messageActionsRegistry = registry.category("mail.message/actions");

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("models").Message} Message */
/** @typedef {import("models").Thread} Thread */
/**
 * @typedef {Object} MessageActionSpecificParams
 * @property {import("@web/env").OdooEnv} [env]
 * @property {Message} message
 * @property {import("@odoo/owl").Signal<boolean>} [messageActive]
 * @property {import("@web/core/dropdown/dropdown_hooks").DropdownState} [optionsDropdown]
 * @property {import("@odoo/owl").Signal<HTMLElement>} [reactionAnchorRef] when set, the anchor element for reactions
 * @property {Thread} [thread] when set, the thread the message is being viewed
 */
/** @typedef {import("@mail/core/common/action").ActionParams<MessageAction, UseMessageActions_Def> & MessageActionSpecificParams} MessageActionParams */
/** @typedef {import("@mail/core/common/action").ActionDefinition<MessageActionParams, MessageAction>} MessageActionDefinition */

/**
 * @param {string} id
 * @param {MessageActionDefinition} definition
 */
export function registerMessageAction(id, definition) {
    messageActionsRegistry.add(id, definition);
}

registerMessageAction("reaction", {
    component: QuickReactionMenu,
    componentProps: ({ action, message, messageActive }) => ({
        action,
        message,
        messageActive: messageActive?.(),
    }),
    componentCondition: ({ reactionAnchorRef }) => !isMobileOS() && !reactionAnchorRef,
    condition: ({ message }) => message.canAddReaction,
    icon: "oi oi-smile-add",
    name: _t("Add a Reaction"),
    onSelected({ reactionAnchorRef, rootRef }) {
        const anchorEl = reactionAnchorRef
            ? reactionAnchorRef()
            : rootRef?.()?.querySelector(`[name="${this.id}"]`);
        return this.reactionPicker.open({ el: anchorEl });
    },
    setup({ message, thread }) {
        this.reactionPicker = useEmojiPicker(undefined, {
            onSelect: (emoji) => {
                const reaction = message.reactions.find(
                    ({ content, personas }) =>
                        content === emoji && thread.effectiveSelf.in(personas)
                );
                if (!reaction) {
                    message.react(emoji);
                }
            },
        });
    },
    sequence: 10,
});
registerMessageAction("reply-to", {
    condition: ({ channel, env, message }) => {
        if (env?.inMessagingMenu) {
            return false;
        }
        if (message.canReplyTo) {
            return true;
        }
        return !channel && !message.isEmpty && message.isNote && !message.isSelfAuthored;
    },
    icon: "fa fa-reply",
    name: _t("Reply"),
    onSelected: ({ env, message, thread }) => {
        const composer = thread.composer;
        if (message.eq(composer.replyToMessage)) {
            composer.replyToMessage = undefined;
            return;
        }
        if (thread.channel) {
            composer.replyToMessage = message;
            return;
        }
        if (!message.isSelfAuthored && message.model !== "discuss.channel" && message.author) {
            composer.insertReplyFromNote(message);
        }
        env?.inChatter?.toggleComposer("note", { force: true });
        composer.restoredFromFullComposer = false;
        if (!composer.isFocused) {
            composer.autofocus++;
        }
    },
    sequence: ({ message }) => (message.isSelfAuthored ? 55 : 20),
});
registerMessageAction("add-bookmark", {
    condition: ({ message }) =>
        message.canToggleBookmark && !message.isEmpty && !message.is_bookmarked,
    icon: "fa fa-bookmark-o",
    name: _t("Bookmark"),
    onSelected: ({ message }) => message.addBookmark(),
    sequence: 80,
});
registerMessageAction("remove-bookmark", {
    condition: ({ message }) => message.canToggleBookmark && message.is_bookmarked,
    icon: "fa fa-bookmark",
    name: _t("Remove from Bookmarks"),
    onSelected: ({ env, message }) => message.removeBookmark(env),
    sequence: 80,
});
registerMessageAction("mark-as-read", {
    condition: ({ message }) => message.needaction,
    icon: "fa fa-check",
    name: _t("Mark as Read"),
    onSelected: ({ message }) => message.setDone(),
    sequence: 35,
});
registerMessageAction("mark-as-unread", {
    condition: ({ message }) => message.canMarkAsUnread,
    icon: "fa fa-eye-slash",
    name: _t("Mark as Unread"),
    onSelected: ({ message }) => message.markAsUnread(),
    sequence: 50,
});
registerMessageAction("reactions", {
    condition: ({ message }) => message.reactions.length,
    icon: "fa fa-smile-o",
    name: _t("View Reactions"),
    onSelected: ({ message, rootRef, store }) => {
        store.env.services.dialog.add(MessageReactionMenu, { message }, { rootRef });
    },
    sequence: 60,
});
registerMessageAction("unfollow", {
    condition: ({ env, message }) => env?.inMessagingMenu && message.thread?.selfFollower,
    icon: "fa fa-user-times",
    name: _t("Unfollow"),
    onSelected: ({ message }) => message.unfollow(),
    sequence: 110,
});
registerMessageAction("edit", {
    condition: ({ env, message }) => !env?.inMessagingMenu && message.editable,
    icon: "fa fa-pencil",
    name: _t("Edit"),
    onSelected: ({ message, optionsDropdown }) => {
        message.enterEditMode();
        optionsDropdown?.close();
    },
    sequence: ({ message }) => (message.isSelfAuthored ? 20 : 115),
});
registerMessageAction("delete", {
    condition: ({ message }) => message.deletable,
    icon: "fa fa-trash",
    name: _t("Delete"),
    onSelected: ({ env, message, rootRef }) => message.showDeleteConfirm(env, rootRef),
    sequence: 120,
    tags: ACTION_TAGS.DANGER,
});
registerMessageAction("download_files", {
    condition: ({ message, store }) =>
        message.attachment_ids.length > 1 && store.self_user?.share === false,
    icon: "fa fa-download",
    name: _t("Download Files"),
    onSelected: ({ message }) =>
        download({
            data: {
                file_ids: message.attachment_ids.map((rec) => rec.id),
                zip_name: `attachments_${DateTime.local().toFormat("HHmmddMMyyyy")}.zip`,
            },
            url: "/mail/attachment/zip",
        }),
    sequence: 55,
});
registerMessageAction("toggle-translation", {
    condition: ({ message }) => message.isTranslatable,
    icon: ({ message }) =>
        `fa fa-language ${message.showTranslation ? "o-mail-Message-translated" : ""}`,
    name: ({ message }) => (message.showTranslation ? _t("Revert") : _t("Translate")),
    onSelected: ({ message }) => message.onClickToggleTranslation(),
    sequence: 100,
});
registerMessageAction("copy-message", {
    condition: ({ message }) => !message.isBodyEmpty,
    onSelected: ({ message }) => message.copyMessageText(),
    name: _t("Copy Text"),
    icon: "fa fa-copy",
    sequence: 85,
});
registerMessageAction("copy-link", {
    condition: ({ message, thread }) =>
        message.message_type &&
        message.message_type !== "user_notification" &&
        thread &&
        (!thread.access_token || thread.hasReadAccess),
    icon: "fa fa-link",
    name: _t("Copy Message Link"),
    onSelected: ({ message }) => message.copyLink(),
    sequence: 90,
});
registerMessageAction("end-poll", {
    condition: ({ message }) =>
        message.poll && !message.poll.end_message_id && message.poll.createdBySelf,
    icon: " oi oi-view-cohort",
    name: _t("End Poll"),
    onSelected: ({ message }) => rpc("/mail/poll/end", { poll_id: message.poll.id }),
    sequence: 115,
});

export class MessageAction extends Action {
    /** @type {import("@web/env").OdooEnv} */
    env;
    /** @type {() => Message} */
    messageFn;
    /** @type {import("@odoo/owl").Signal<boolean>} */
    messageActive;
    /** @type {import("@web/core/dropdown/dropdown_hooks").DropdownState} */
    optionsDropdown;
    /** @type {import("@odoo/owl").Signal<HTMLElement>} */
    reactionAnchorRef;
    /** @type {() => Thread} */
    threadFn;
    /**
     * @param {Object} param0
     * @param {import("@web/env").OdooEnv} [param0.env]
     * @param {Message|() => Message} param0.message
     * @param {import("@odoo/owl").Signal<boolean>} [param0.messageActive]
     * @param {import("@web/core/dropdown/dropdown_hooks").DropdownState} [param0.optionsDropdown]
     * @param {import("@odoo/owl").Signal<HTMLElement>} [param0.reactionAnchorRef]
     * @param {Thread|() => Thread} [param0.thread]
     */
    constructor({ env, message, messageActive, optionsDropdown, reactionAnchorRef, thread }) {
        super(...arguments);
        this.env = env;
        this.messageFn = typeof message === "function" ? message : () => message;
        this.messageActive = messageActive;
        this.optionsDropdown = optionsDropdown;
        this.reactionAnchorRef = reactionAnchorRef;
        this.threadFn = typeof thread === "function" ? thread : () => thread;
    }

    get params() {
        const thread = this.threadFn();
        return Object.assign(super.params, {
            env: this.env,
            message: this.messageFn(),
            channel: thread?.channel,
            messageActive: this.messageActive,
            optionsDropdown: this.optionsDropdown,
            reactionAnchorRef: this.reactionAnchorRef,
            thread,
        });
    }
}

/** @typedef {UseActions<MessageActionParams, MessageAction>} UseMessageActions_Def */
class UseMessageActions extends UseActions {
    ActionClass = MessageAction;
}

/**
 * @param {import("@mail/core/common/action").ActionRootRefParam & {env?: import("@web/env").OdooEnv, message?: Message|() => Message, messageActive?: import("@odoo/owl").Signal<boolean>, optionsDropdown?: import("@web/core/dropdown/dropdown_hooks").DropdownState, reactionAnchorRef?: import("@odoo/owl").Signal<HTMLElement>, thread?: Thread|() => Thread}} [params0={}]
 *   `env`: when set, the env the message is viewed in. `messageActive`: when set, whether the message row is
 *   active. `optionsDropdown`: when set, the message's options dropdown. `reactionAnchorRef`: when set, the
 *   anchor element for reactions. `thread`: when set, the thread the message is being viewed.
 * @returns {UseMessageActions_Def}
 */
export function useMessageActions({
    env,
    message,
    messageActive,
    optionsDropdown,
    reactionAnchorRef,
    rootRef,
    thread,
} = {}) {
    return useAction(messageActionsRegistry, UseMessageActions, MessageAction, {
        env,
        message,
        messageActive,
        optionsDropdown,
        reactionAnchorRef,
        rootRef,
        thread,
    });
}
