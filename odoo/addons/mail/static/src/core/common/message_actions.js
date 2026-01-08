/* @odoo-module */

import { useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { MessageReactionButton } from "./message_reaction_button";

const { DateTime } = luxon;

export const messageActionsRegistry = registry.category("mail.message/actions");

messageActionsRegistry
    .add("reaction", {
        callComponent: MessageReactionButton,
        props: (component) => ({ message: component.props.message }),
        condition: (component) => component.canAddReaction,
        sequence: 10,
    })
    .add("reply-to", {
        condition: (component) => component.canReplyTo,
        icon: "fa-reply",
        title: _t("Reply"),
        onClick: (component) => component.onClickReplyTo(),
        sequence: (component) => (component.isInInbox ? 55 : 20),
    })
    .add("toggle-star", {
        condition: (component) => component.canToggleStar,
        icon: (component) =>
            component.props.message.isStarred ? "fa-star o-mail-Message-starred" : "fa-star-o",
        title: _t("Mark as Todo"),
        onClick: (component) => component.messageService.toggleStar(component.props.message),
        sequence: 30,
    })
    .add("mark-as-read", {
        condition: (component) => component.isInInbox,
        icon: "fa-check",
        title: _t("Mark as Read"),
        onClick: (component) => component.messageService.setDone(component.props.message),
        sequence: 40,
    })
    .add("reactions", {
        condition: (component) => component.message.reactions.length,
        icon: "fa-smile-o",
        title: _t("View Reactions"),
        onClick: (component) => component.openReactionMenu(),
        sequence: 50,
        dropdown: true,
    })
    .add("unfollow", {
        condition: (component) => component.showUnfollow,
        icon: "fa-user-times",
        title: _t("Unfollow"),
        onClick: (component) => component.messageService.unfollow(component.props.message),
        sequence: 60,
    })
    .add("mark-as-unread", {
        condition: (component) =>
            component.props.thread.model === "discuss.channel" && component.store.user,
        icon: "fa-eye-slash",
        title: _t("Mark as Unread"),
        onClick: (component) => component.onClickMarkAsUnread(),
        sequence: 70,
    })
    .add("edit", {
        condition: (component) => component.editable,
        icon: "fa-pencil",
        title: _t("Edit"),
        onClick: (component) => component.onClickEdit(),
        sequence: 80,
    })
    .add("delete", {
        condition: (component) => component.deletable,
        icon: "fa-trash",
        title: _t("Delete"),
        onClick: (component) => component.onClickDelete(),
        sequence: 90,
    })
    .add("download_files", {
        condition: (component) =>
            component.message.attachments.length > 1 && component.store.self?.user?.isInternalUser,
        icon: "fa-download",
        title: _t("Download Files"),
        onClick: (component) =>
            download({
                data: {
                    file_ids: component.message.attachments.map((rec) => rec.id),
                    zip_name: `attachments_${DateTime.local().toFormat("HHmmddMMyyyy")}.zip`,
                },
                url: "mail/attachment/zip",
            }),
        sequence: 55,
    })
    .add("toggle-translation", {
        condition: (component) => component.translatable,
        icon: (component) =>
            `fa-language ${component.state.showTranslation ? "o-mail-Message-translated" : ""}`,
        title: (component) => (component.state.showTranslation ? _t("Revert") : _t("Translate")),
        onClick: (component) => component.onClickToggleTranslation(),
        sequence: 100,
    });

function transformAction(component, id, action) {
    return {
        component: action.component,
        id,
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
        callComponent: action.callComponent,
        get props() {
            return action.props(component);
        },
        /**
         * Action to execute when this action is click.
         *
         * @param {object} [param0]
         * @param {boolean} [param0.keepPrevious] Whether the previous action
         * should be kept so that closing the current action goes back
         * to the previous one.
         * */
        onClick() {
            action.onClick?.(component);
        },
        /** Determines the order of this action (smaller first). */
        get sequence() {
            return typeof action.sequence === "function"
                ? action.sequence(component)
                : action.sequence;
        },
    };
}

export function useMessageActions() {
    const component = useComponent();
    const transformedActions = messageActionsRegistry
        .getEntries()
        .map(([id, action]) => transformAction(component, id, action));
    const state = useState({
        get actions() {
            return transformedActions
                .filter((action) => action.condition)
                .sort((a1, a2) => a1.sequence - a2.sequence);
        },
    });
    return state;
}
