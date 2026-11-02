import { Action, IS_ACTION_DEFINITION_SYM, useAction, UseActions } from "@mail/core/common/action";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { formatList } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";

export const messagingMenuTabActionsRegistry = registry.category("mail.messaging_menu_tab/actions");

/** @typedef {import("models").MessagingMenuTab} MessagingMenuTab */
/** @typedef {import("@mail/core/public_web/messaging_menu/messaging_menu_tab_model").MessagingMenuTabDomain} MessagingMenuTabDomain */
/**
 * @typedef {Object} MessagingMenuTabActionSpecificParams
 * @property {MessagingMenuTab} [tab]
 * @property {MessagingMenuTabDomain} [domain] The part of the tab the actions apply to.
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

/**
 * Name of the action marking `domain` as read, telling when a search or a filter other than the
 * default one narrows it.
 *
 * @param {MessagingMenuTabDomain} [domain]
 */
function getMarkAsReadName(domain) {
    return domain?.searchTerm || domain?.filters.some((f) => !f.isDefault)
        ? _t("Mark filtered as read")
        : _t("Mark all read");
}

/**
 * Confirmation of the action marking `domain` as read, naming the tab and what narrows it.
 *
 * @param {MessagingMenuTab} tab
 * @param {MessagingMenuTabDomain} [domain]
 */
function getMarkAsReadConfirmation(tab, domain) {
    const { filters, searchTerm } = domain ?? tab.getCounterDomain();
    const params = {
        filters: formatList(filters.map((f) => `"${f.text}"`)),
        search_term: searchTerm,
        tab_name: tab.label,
    };
    if (filters.length && searchTerm) {
        return _t(
            'Everything in "%(tab_name)s" matching %(filters)s and the search "%(search_term)s" will be marked as read.',
            params
        );
    }
    if (filters.length) {
        return _t(
            'Everything in "%(tab_name)s" matching %(filters)s will be marked as read.',
            params
        );
    }
    if (searchTerm) {
        return _t(
            'Everything in "%(tab_name)s" matching the search "%(search_term)s" will be marked as read.',
            params
        );
    }
    return _t('Everything in "%(tab_name)s" will be marked as read.', params);
}

registerMessagingMenuTabAction("mark-all-read", {
    // The messaging menu stays open behind the dialog, to see the outcome once confirmed.
    closingModeAsDropdown: "closest",
    condition: ({ tab, domain }) => tab?.canMarkAllAsRead(domain),
    disabledCondition: ({ tab, domain }) => !tab.hasUnread(domain ?? tab.getCounterDomain()),
    icon: "check",
    name: ({ domain }) => getMarkAsReadName(domain),
    onSelected: ({ store, tab, domain }) => {
        const name = getMarkAsReadName(domain);
        store.env.services.dialog.add(ConfirmationDialog, {
            title: name,
            body: getMarkAsReadConfirmation(tab, domain),
            confirmLabel: name,
            confirm: () => tab.markAllAsRead(domain),
            cancel: () => {},
        });
    },
    sequence: 10,
});

export class MessagingMenuTabAction extends Action {
    /** @type {() => MessagingMenuTab|undefined} */
    tabFn;
    /** @type {(() => MessagingMenuTabDomain)|undefined} */
    domainFn;

    /**
     * @param {Object} param0
     * @param {() => MessagingMenuTab|undefined} param0.tab
     * @param {() => MessagingMenuTabDomain} [param0.domain]
     */
    constructor({ tab, domain }) {
        super(...arguments);
        this.tabFn = tab;
        this.domainFn = domain;
    }

    get params() {
        return Object.assign(super.params, { tab: this.tabFn(), domain: this.domainFn?.() });
    }
}

/** @typedef {UseActions<MessagingMenuTabActionParams, MessagingMenuTabAction>} UseMessagingMenuTabActions_Def */
class UseMessagingMenuTabActions extends UseActions {
    ActionClass = MessagingMenuTabAction;
}

/**
 * @param {Object} param0
 * @param {() => MessagingMenuTab|undefined} param0.tab The tab the actions apply to.
 * @param {() => MessagingMenuTabDomain} [param0.domain] The part of the tab the actions apply to.
 * @returns {UseMessagingMenuTabActions_Def}
 */
export function useMessagingMenuTabActions({ tab, domain }) {
    return useAction(
        messagingMenuTabActionsRegistry,
        UseMessagingMenuTabActions,
        MessagingMenuTabAction,
        { tab, domain }
    );
}
