import { toRaw, useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { discussComponentRegistry } from "./discuss_component_registry";
import { Deferred } from "@web/core/utils/concurrency";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { convertBrToLineBreak } from "@mail/utils/common/format";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";

const { DateTime } = luxon;

export const messageActionsRegistry = registry.category("mail.message/actions");

messageActionsRegistry
    .add("reaction", {
        component: QuickReactionMenu,
        props: (component) => ({
            message: component.props.message,
            action: messageActionsRegistry.get("reaction"),
            messageActive: component.isActive,
        }),
        condition: (component) => component.props.message.canAddReaction(component.props.thread),
        icon: "oi oi-smile-add",
        title: _t("Add a Reaction"),
        onClick: async (component, action) =>
            component.reactionPicker.open({
                el: component.root?.el?.querySelector(`[name="${action.id}"]`),
            }),
        setup() {
            const component = useComponent();
            component.reactionPicker = useEmojiPicker(undefined, {
                onSelect: (emoji) => {
                    const reaction = component.props.message.reactions.find(
                        ({ content, personas }) =>
                            content === emoji &&
                            personas.find((persona) => persona.eq(component.store.self))
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
        title: _t("Reply"),
        onClick: (component) => {
            const message = toRaw(component.props.message);
            const thread = toRaw(component.props.thread);
            component.props.messageToReplyTo.toggle(thread, message);
        },
        sequence: (component) => (component.props.thread?.eq(component.store.inbox) ? 55 : 20),
    })
    .add("toggle-star", {
        condition: (component) => component.props.message.canToggleStar,
        icon: (component) =>
            component.props.message.starred ? "fa fa-star o-mail-Message-starred" : "fa fa-star-o",
        title: _t("Mark as Todo"),
        onClick: (component) => component.props.message.toggleStar(),
        sequence: 30,
        mobileCloseAfterClick: false,
    })
    .add("mark-as-read", {
        condition: (component) => component.props.thread?.eq(component.store.inbox),
        icon: "fa fa-check",
        title: _t("Mark as Read"),
        onClick: (component) => component.props.message.setDone(),
        sequence: 40,
    })
    .add("reactions", {
        condition: (component) => component.message.reactions.length,
        icon: "fa fa-smile-o",
        title: _t("View Reactions"),
        onClick: (component) => component.openReactionMenu(),
        sequence: 50,
        dropdown: true,
    })
    .add("unfollow", {
        condition: (component) => component.props.message.canUnfollow(component.props.thread),
        icon: "fa fa-user-times",
        title: _t("Unfollow"),
        onClick: (component) => component.props.message.unfollow(),
        sequence: 60,
    })
    .add("edit", {
        condition: (component) => component.props.message.editable,
        icon: "fa fa-pencil",
        title: _t("Edit"),
        onClick: (component) => {
            const message = toRaw(component.props.message);
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
            component.state.isEditing = true;
        },
        sequence: 80,
    })
    .add("delete", {
        condition: (component) => component.props.message.editable,
        icon: "fa fa-trash",
        title: _t("Delete"),
        onClick: async (component) => {
            const message = toRaw(component.message);
            const def = new Deferred();
            component.dialog.add(
                discussComponentRegistry.get("MessageConfirmDialog"),
                {
                    message,
                    prompt: _t("Are you sure you want to delete this message?"),
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
        sequence: 90,
    })
    .add("download_files", {
        condition: (component) =>
            component.message.attachment_ids.length > 1 && component.store.self.isInternalUser,
        icon: "fa fa-download",
        title: _t("Download Files"),
        onClick: (component) =>
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
        title: (component) => (component.state.showTranslation ? _t("Revert") : _t("Translate")),
        onClick: (component) => component.onClickToggleTranslation(),
        sequence: 100,
    })
    .add("copy-link", {
        condition: (component) =>
            component.message.message_type &&
            component.message.message_type !== "user_notification",
        icon: "fa fa-link",
        title: _t("Copy Link"),
        onClick: (component) => component.message.copyLink(),
        sequence: 110,
    });

function transformAction(component, id, action) {
    return {
        component: action.component,
        id,
        mobileCloseAfterClick: action.mobileCloseAfterClick ?? true,
        /** Condition to display this action. */
        get condition() {
            return action.condition(component);
        },
        /** Icon for the button this action. */
        get icon() {
            return typeof action.icon === "function" ? action.icon(component) : action.icon;
        },
        /** title of this action, displayed to the user. */
        get title() {
            return typeof action.title === "function" ? action.title(component) : action.title;
        },
        get props() {
            return action.props(component);
        },
        onClick(ev) {
            return action.onClick?.(component, this, ev);
        },
        /** Determines the order of this action (smaller first). */
        get sequence() {
            return typeof action.sequence === "function"
                ? action.sequence(component)
                : action.sequence;
        },
        /** Component setup to execute when this action is registered. */
        setup: action.setup,
    };
}

export function useMessageActions() {
    const component = useComponent();
    const transformedActions = messageActionsRegistry
        .getEntries()
        .map(([id, action]) => transformAction(component, id, action));
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
