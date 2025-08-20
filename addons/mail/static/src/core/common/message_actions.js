import { toRaw, useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { discussComponentRegistry } from "./discuss_component_registry";
import { Deferred } from "@web/core/utils/concurrency";
import { Action, ACTION_TAGS, UseActions } from "@mail/core/common/action";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export const messageActionsRegistry = registry.category("mail.message/actions");

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("@mail/core/common/action").ActionDefinition} ActionDefinition */
/** @typedef {import("models").Message} Message */
/** @typedef {import("models").Thread} Thread */
/**
 * @typedef {Object} MessageActionSpecificDefinition
 * @property {boolean|(comp: Component) => boolean} [condition=true]
 */
/**
 * @typedef {ActionDefinition & MessageActionSpecificDefinition} MessageActionDefinition
 */
/**
 * @param {string} id
 * @param {MessageActionDefinition} definition
 */
export function registerMessageAction(id, definition) {
    messageActionsRegistry.add(id, definition);
}

registerMessageAction("reaction", {
    component: QuickReactionMenu,
    componentProps: ({ message, owner }) => ({
        message,
        action: messageActionsRegistry.get("reaction"),
        messageActive: owner.isActive,
    }),
    componentCondition: () => !isMobileOS(),
    condition: ({ message, thread }) => message.canAddReaction(thread),
    icon: "oi oi-smile-add",
    name: _t("Add a Reaction"),
    onSelected({ owner }) {
        return owner.reactionPicker.open({
            el: owner.root?.el?.querySelector(`[name="${this.id}"]`),
        });
    },
    setup: ({ message, owner, thread }) =>
        (owner.reactionPicker = useEmojiPicker(undefined, {
            onSelect: (emoji) => {
                const reaction = message.reactions.find(
                    ({ content, personas }) =>
                        content === emoji && thread.effectiveSelf.in(personas)
                );
                if (!reaction) {
                    message.react(emoji);
                }
            },
        })),
    sequence: 10,
});
registerMessageAction("reply-to", {
    condition: ({ message: msg, thread: thr }) => {
        const message = toRaw(msg);
        const thread = toRaw(thr);
        return (
            message.canReplyTo(thread) ||
            (!["discuss.channel", "mail.box"].includes(thread?.model) &&
                message.isNote &&
                !message.isSelfAuthored)
        );
    },
    icon: "fa fa-reply",
    name: _t("Reply"),
    onSelected: ({ message: msg, owner, thread: thr }) => {
        const message = toRaw(msg);
        const thread = toRaw(thr);
        const composer = thread.composer;
        if (message.eq(composer.replyToMessage)) {
            composer.replyToMessage = undefined;
            return;
        }
        if (["discuss.channel", "mail.box"].includes(thread.model)) {
            composer.replyToMessage = message;
        }
        if (thread.model === "discuss.channel") {
            return;
        }
        if (!message.isSelfAuthored && message.model !== "discuss.channel") {
            const mentionText = `@${message.authorName} `;
            if (!composer.composerText.includes(mentionText)) {
                composer.mentionedPartners.add(message.author);
                composer.insertText(mentionText, 0, { moveCursorToEnd: true });
            }
        }
        owner.env.inChatter?.toggleComposer("note", { force: true });
    },
    sequence: ({ message, store, thread }) =>
        thread?.eq(store.inbox) || message.isSelfAuthored ? 55 : 20,
});
registerMessageAction("toggle-star", {
    condition: ({ message }) => message.canToggleStar,
    icon: ({ message }) => (message.starred ? "fa fa-star o-mail-Message-starred" : "fa fa-star-o"),
    name: ({ message }) => (message.starred ? _t("Remove Star") : _t("Add Star")),
    onSelected: ({ message }) => message.toggleStar(),
    sequence: 30,
});
registerMessageAction("mark-as-read", {
    condition: ({ store, thread }) => thread?.eq(store.inbox),
    icon: "fa fa-check",
    name: _t("Mark as Read"),
    onSelected: ({ message }) => message.setDone(),
    sequence: 40,
});
registerMessageAction("reactions", {
    condition: ({ message }) => message.reactions.length,
    icon: "fa fa-smile-o",
    name: _t("View Reactions"),
    onSelected: ({ owner }) => owner.openReactionMenu(),
    sequence: 50,
});
registerMessageAction("unfollow", {
    condition: ({ message, thread }) => message.canUnfollow(thread),
    icon: "fa fa-user-times",
    name: _t("Unfollow"),
    onSelected: ({ message }) => message.unfollow(),
    sequence: 60,
});
registerMessageAction("edit", {
    condition: ({ message }) => message.editable,
    icon: "fa fa-pencil",
    name: _t("Edit"),
    onSelected: ({ message, owner, thread }) => {
        message.enterEditMode(thread);
        owner.optionsDropdown?.close();
    },
    sequence: ({ message }) => (message.isSelfAuthored ? 20 : 55),
});
registerMessageAction("delete", {
    condition: ({ message }) => message.editable,
    icon: "fa fa-trash",
    name: _t("Delete"),
    onSelected: async ({ message: msg, owner, store }) => {
        const message = toRaw(msg);
        const def = new Deferred();
        store.env.services.dialog.add(
            discussComponentRegistry.get("MessageConfirmDialog"),
            {
                message,
                prompt: _t("Are you sure you want to bid farewell to this message forever?"),
                onConfirm: () => {
                    def.resolve(true);
                    message.remove({
                        removeFromThread: owner.shouldHideFromMessageListOnDelete,
                    });
                },
            },
            { context: owner, onClose: () => def.resolve(false) }
        );
        return def;
    },
    sequence: 120,
    tags: ACTION_TAGS.DANGER,
});
registerMessageAction("download_files", {
    condition: ({ message, store }) =>
        message.attachment_ids.length > 1 && store.self.main_user_id?.share === false,
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
    condition: ({ message }) => message.isTranslatable(message.thread),
    icon: ({ message }) =>
        `fa fa-language ${message.showTranslation ? "o-mail-Message-translated" : ""}`,
    name: ({ message }) => (message.showTranslation ? _t("Revert") : _t("Translate")),
    onSelected: ({ message }) => message.onClickToggleTranslation(),
    sequence: 100,
});
registerMessageAction("copy-message", {
    condition: ({ message }) => isMobileOS() && !message.isBodyEmpty,
    onSelected: ({ message }) => message.copyMessageText(),
    name: _t("Copy to Clipboard"),
    icon: "fa fa-copy",
    sequence: 30,
});
registerMessageAction("copy-link", {
    condition: ({ message, thread }) =>
        message.message_type &&
        message.message_type !== "user_notification" &&
        thread &&
        (!thread.access_token || thread.hasReadAccess),
    icon: "fa fa-link",
    name: _t("Copy Link"),
    onSelected: ({ message }) => message.copyLink(),
    sequence: 110,
});

export class MessageAction extends Action {
    /** @type {() => Message} */
    messageFn;
    /** @type {() => Thread} */
    threadFn;
    /**
     * @param {Object} param0
     * @param {Thread|() => Thread} thread
     */
    constructor({ message, thread }) {
        super(...arguments);
        this.messageFn = typeof message === "function" ? message : () => message;
        this.threadFn = typeof thread === "function" ? thread : () => thread;
    }

    get params() {
        return Object.assign(super.params, { message: this.messageFn(), thread: this.threadFn() });
    }
}

class UseMessageActions extends UseActions {
    ActionClass = MessageAction;
}

/**
 * @param {Object} [params0={}]
 * @param {Message|() => Message} [message]
 * @param {Thread|() => Thread} [thread] when set, the thread the message is being viewed
 */
export function useMessageActions({ message, thread } = {}) {
    const component = useComponent();
    const transformedActions = messageActionsRegistry
        .getEntries()
        .map(
            ([id, definition]) =>
                new MessageAction({ owner: component, id, definition, message, thread })
        );
    for (const action of transformedActions) {
        action.setup();
    }
    const state = useState(
        new UseMessageActions(component, transformedActions, useService("mail.store"))
    );
    return state;
}
