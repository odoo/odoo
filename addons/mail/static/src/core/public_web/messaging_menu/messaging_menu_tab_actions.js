import { Action, IS_ACTION_DEFINITION_SYM, useAction, UseActions } from "@mail/core/common/action";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const messagingMenuTabActionsRegistry = registry.category("mail.messaging_menu_tab/actions");

/** @typedef {import("models").MessagingMenuTab} MessagingMenuTab */
/**
 * @typedef {Object} MessagingMenuTabActionSpecificParams
 * @property {MessagingMenuTab} [tab]
 */
/** @typedef {import("@mail/core/common/action").ActionParams<MessagingMenuTabAction, UseMessagingMenuTabActions_Def> & MessagingMenuTabActionSpecificParams} MessagingMenuTabActionParams */
/** @typedef {import("@mail/core/common/action").ActionDefinition<MessagingMenuTabActionParams, MessagingMenuTabAction>} MessagingMenuTabActionDefinition */

/**
 * @param {string} id
 * @param {MessagingMenuTabActionDefinition} definition
 */
export function registerMessagingMenuTabAction(id, definition) {
    messagingMenuTabActionsRegistry.add(
        id,
        Object.assign(definition, { [IS_ACTION_DEFINITION_SYM]: true })
    );
}

registerMessagingMenuTabAction("mark-all-read", {
    // The messaging menu stays open behind the dialog, to see the outcome once confirmed.
    closingModeAsDropdown: "closest",
    condition: ({ tab }) => tab?.canMarkAllAsRead,
    icon: "check",
    name: _t("Mark all read"),
    onSelected: ({ store, tab }) => {
        store.env.services.dialog.add(ConfirmationDialog, {
            title: _t("Mark all read"),
            body: _t('Everything in "%(tab_name)s" will be marked as read.', {
                tab_name: tab.label,
            }),
            confirmLabel: _t("Mark all read"),
            confirm: () => tab.markAllAsRead(),
            cancel: () => {},
        });
    },
    sequence: 10,
});

export class MessagingMenuTabAction extends Action {
    /** @type {() => MessagingMenuTab|undefined} */
    tabFn;

    /**
     * @param {Object} param0
     * @param {() => MessagingMenuTab|undefined} param0.tab
     */
    constructor({ tab }) {
        super(...arguments);
        this.tabFn = tab;
    }

    get params() {
        return Object.assign(super.params, { tab: this.tabFn() });
    }
}

/** @typedef {UseActions<MessagingMenuTabActionParams, MessagingMenuTabAction>} UseMessagingMenuTabActions_Def */
class UseMessagingMenuTabActions extends UseActions {
    ActionClass = MessagingMenuTabAction;
}

/**
 * @param {Object} param0
 * @param {() => MessagingMenuTab|undefined} param0.tab The tab the actions apply to.
 * @returns {UseMessagingMenuTabActions_Def}
 */
export function useMessagingMenuTabActions({ tab }) {
    return useAction(
        messagingMenuTabActionsRegistry,
        UseMessagingMenuTabActions,
        MessagingMenuTabAction,
        { tab }
    );
}
