import { toRaw, useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { discussComponentRegistry } from "./discuss_component_registry";
import { Deferred } from "@web/core/utils/concurrency";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { Action } from "./action";

const { DateTime } = luxon;

export const messageActionsRegistry = registry.category("mail.message/actions");

messageActionsRegistry
    .add("reaction", {
        component: QuickReactionMenu,
        componentProps: (component) => ({
            message: component.props.message,
            action: messageActionsRegistry.get("reaction"),
            messageActive: component.isActive,
        }),
        componentCondition: () => !isMobileOS(),
        condition: (component) => component.props.message.canAddReaction(component.props.thread),
        icon: "oi oi-smile-add",
        iconLarge: "oi fa-lg oi-smile-add",
        name: _t("Add a Reaction"),
        onSelected: async (component, action) =>
            component.reactionPicker.open({
                el: component.root?.el?.querySelector(`[name="${action.id}"]`),
            }),
        setup() {
            const component = useComponent();
            component.reactionPicker = useEmojiPicker(undefined, {
                onSelect: (emoji) => {
                    const reaction = component.props.message.reactions.find(
                        ({ content, personas }) =>
                            content === emoji && component.props.thread.effectiveSelf.in(personas)
                    );
                    if (!reaction) {
                        component.props.message.react(emoji);
                    }
                },
            });
        },
        sequence: 10,
    })
    .add("reply-to", {
        condition: (component) => component.props.message.canReplyTo(component.props.thread),
        icon: "fa fa-reply",
        iconLarge: "fa fa-lg fa-reply",
        name: _t("Reply"),
        onSelected: (component) => {
            const message = toRaw(component.props.message);
            const thread = toRaw(component.props.thread);
            if (message.eq(thread.composer.replyToMessage)) {
                thread.composer.replyToMessage = undefined;
            } else {
                thread.composer.replyToMessage = message;
            }
        },
        sequence: (component) =>
            component.props.thread?.eq(component.store.inbox) ||
            component.props.message.isSelfAuthored
                ? 55
                : 20,
    })
    .add("toggle-star", {
        condition: (component) => component.props.message.canToggleStar,
        icon: (component) =>
            component.props.message.starred ? "fa fa-star o-mail-Message-starred" : "fa fa-star-o",
        iconLarge: (component) =>
            component.props.message.starred
                ? "fa fa-lg fa-star o-mail-Message-starred"
                : "fa fa-lg fa-star-o",
        name: _t("Mark as Todo"),
        onSelected: (component) => component.props.message.toggleStar(),
        sequence: 30,
    })
    .add("mark-as-read", {
        condition: (component) => component.props.thread?.eq(component.store.inbox),
        icon: "fa fa-check",
        iconLarge: "fa fa-lg fa-check",
        name: _t("Mark as Read"),
        onSelected: (component) => component.props.message.setDone(),
        sequence: 40,
    })
    .add("reactions", {
        condition: (component) => component.message.reactions.length,
        icon: "fa fa-smile-o",
        iconLarge: "fa fa-lg fa-smile-o",
        name: _t("View Reactions"),
        onSelected: (component) => component.openReactionMenu(),
        sequence: 50,
    })
    .add("unfollow", {
        condition: (component) => component.props.message.canUnfollow(component.props.thread),
        icon: "fa fa-user-times",
        iconLarge: "fa fa-lg fa-user-times",
        name: _t("Unfollow"),
        onSelected: (component) => component.props.message.unfollow(),
        sequence: 60,
    })
    .add("edit", {
        condition: (component) => component.props.message.editable,
        icon: "fa fa-pencil",
        iconLarge: "fa fa-lg fa-pencil",
        name: _t("Edit"),
        onSelected: (component) => {
            component.props.message.enterEditMode(component.props.thread);
            component.optionsDropdown?.close();
        },
        sequence: (component) => (component.props.message.isSelfAuthored ? 20 : 55),
    })
    .add("delete", {
        condition: (component) => component.props.message.editable,
        icon: "fa fa-trash",
        iconLarge: "fa fa-lg fa-trash",
        name: _t("Delete"),
        danger: true,
        onSelected: async (component) => {
            const message = toRaw(component.message);
            const def = new Deferred();
            component.dialog.add(
                discussComponentRegistry.get("MessageConfirmDialog"),
                {
                    message,
                    prompt: _t("Are you sure you want to bid farewell to this message forever?"),
                    onConfirm: () => {
                        def.resolve(true);
                        message.remove();
                    },
                },
                { context: component, onClose: () => def.resolve(false) }
            );
            return def;
        },
        setup: () => {
            const component = useComponent();
            component.dialog = useService("dialog");
        },
        sequence: 120,
    })
    .add("download_files", {
        condition: (component) =>
            component.message.attachment_ids.length > 1 &&
            component.store.self.main_user_id?.share === false,
        icon: "fa fa-download",
        iconLarge: "fa fa-lg fa-download",
        name: _t("Download Files"),
        onSelected: (component) =>
            download({
                data: {
                    file_ids: component.message.attachment_ids.map((rec) => rec.id),
                    zip_name: `attachments_${DateTime.local().toFormat("HHmmddMMyyyy")}.zip`,
                },
                url: "/mail/attachment/zip",
            }),
        sequence: 55,
    })
    .add("toggle-translation", {
        condition: (component) => component.props.message.isTranslatable(component.props.thread),
        icon: (component) =>
            `fa fa-language ${component.state.showTranslation ? "o-mail-Message-translated" : ""}`,
        iconLarge: (component) =>
            `fa fa-lg fa-language ${
                component.state.showTranslation ? "o-mail-Message-translated" : ""
            }`,
        name: (component) => (component.state.showTranslation ? _t("Revert") : _t("Translate")),
        onSelected: (component) => component.onClickToggleTranslation(),
        sequence: 100,
    })
    .add("copy-message", {
        condition: (component) => isMobileOS() && !component.message.isBodyEmpty,
        onSelected: (component) => component.message.copyMessageText(),
        name: _t("Copy to Clipboard"),
        icon: "fa fa-copy",
        iconLarge: "fa fa-lg fa-copy",
        sequence: 25,
    })
    .add("copy-link", {
        condition: (component) =>
            component.message.message_type &&
            component.message.message_type !== "user_notification" &&
            (!component.props.thread.access_token || component.props.thread.hasReadAccess),
        icon: "fa fa-link",
        iconLarge: "fa fa-lg fa-link",
        name: _t("Copy Link"),
        onSelected: (component) => component.message.copyLink(),
        sequence: 110,
    });

class MessageAction extends Action {
    /** Condition to display this action. */
    get condition() {
        return messageActionsInternal.condition(this._component, this.id, this.explicitDefinition);
    }
}

export const messageActionsInternal = {
    condition(component, id, action) {
        if (!action?.condition) {
            return true;
        }
        return typeof action.condition === "function"
            ? action.condition(component)
            : action.condition;
    },
    sequence(component, id, action) {
        return typeof action.sequence === "function" ? action.sequence(component) : action.sequence;
    },
};

export function useMessageActions() {
    const component = useComponent();
    const transformedActions = messageActionsRegistry
        .getEntries()
        .map(([id, action]) => new MessageAction(component, id, action));
    for (const action of transformedActions) {
        if (action.setup) {
            action.setup(action);
        }
    }
    const state = useState({
        get actions() {
            const actions = transformedActions
                .filter((action) => action.condition)
                .sort((a1, a2) => a1.sequence - a2.sequence);
            if (actions.length > 0) {
                actions.at(0).isFirst = true;
                actions.at(-1).isLast = true;
            }
            return actions;
        },
    });
    return state;
}
