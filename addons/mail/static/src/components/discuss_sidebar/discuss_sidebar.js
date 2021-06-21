/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { AutocompleteInput } from '@mail/components/autocomplete_input/autocomplete_input';
import { DiscussSidebarItem } from '@mail/components/discuss_sidebar_item/discuss_sidebar_item';

const { Component } = owl;
const { useRef } = owl.hooks;

const components = { AutocompleteInput, DiscussSidebarItem };

export class DiscussSidebar extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useModels();
        useUpdate({ func: () => this._update() });
        /**
         * Reference of the quick search input. Useful to filter channels and
         * chats based on this input content.
         */
        this._quickSearchInputRef = useRef('quickSearchInput');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    /**
     * @returns {string}
     */
    get FIND_OR_CREATE_CHANNEL() {
        return this.env._t("Find or create a channel...");
    }

    /**
     * @returns {mail.thread[]}
     */
    get orderedMailboxes() {
        return this.env.models['mail.thread']
            .all(thread => thread.isPinned && thread.model === 'mail.box')
            .sort((mailbox1, mailbox2) => {
                if (mailbox1 === this.env.messaging.inbox) {
                    return -1;
                }
                if (mailbox2 === this.env.messaging.inbox) {
                    return 1;
                }
                if (mailbox1 === this.env.messaging.starred) {
                    return -1;
                }
                if (mailbox2 === this.env.messaging.starred) {
                    return 1;
                }
                const mailbox1Name = mailbox1.displayName;
                const mailbox2Name = mailbox2.displayName;
                mailbox1Name < mailbox2Name ? -1 : 1;
            });
    }

    /**
     * Return the list of chats that match the quick search value input.
     *
     * @returns {mail.thread[]}
     */
    get quickSearchPinnedAndOrderedChats() {
        const allOrderedAndPinnedChats = this.env.models['mail.thread']
            .all(thread =>
                thread.channel_type === 'chat' &&
                thread.isPinned &&
                thread.model === 'mail.channel'
            )
            .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
        if (!this.discuss.sidebarQuickSearchValue) {
            return allOrderedAndPinnedChats;
        }
        const qsVal = this.discuss.sidebarQuickSearchValue.toLowerCase();
        return allOrderedAndPinnedChats.filter(chat => {
            const nameVal = chat.displayName.toLowerCase();
            return nameVal.includes(qsVal);
        });
    }

    /**
     * Return the list of channels that match the quick search value input.
     *
     * @returns {mail.thread[]}
     */
    get quickSearchOrderedAndPinnedMultiUserChannels() {
        const allOrderedAndPinnedMultiUserChannels = this.env.models['mail.thread']
            .all(thread =>
                thread.channel_type === 'channel' &&
                thread.isPinned &&
                thread.model === 'mail.channel'
            )
            .sort((c1, c2) => {
                if (c1.displayName && !c2.displayName) {
                    return -1;
                } else if (!c1.displayName && c2.displayName) {
                    return 1;
                } else if (c1.displayName && c2.displayName && c1.displayName !== c2.displayName) {
                    return c1.displayName.toLowerCase() < c2.displayName.toLowerCase() ? -1 : 1;
                } else {
                    return c1.id - c2.id;
                }
            });
        if (!this.discuss.sidebarQuickSearchValue) {
            return allOrderedAndPinnedMultiUserChannels;
        }
        const qsVal = this.discuss.sidebarQuickSearchValue.toLowerCase();
        return allOrderedAndPinnedMultiUserChannels.filter(channel => {
            const nameVal = channel.displayName.toLowerCase();
            return nameVal.includes(qsVal);
        });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (!this.discuss) {
            return;
        }
        if (this._quickSearchInputRef.el) {
            this._quickSearchInputRef.el.value = this.discuss.sidebarQuickSearchValue;
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on channel title.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickChannelTitle(ev) {
        ev.stopPropagation();
        return this.env.bus.trigger('do-action', {
            action: {
                name: this.env._t("Public Channels"),
                type: 'ir.actions.act_window',
                res_model: 'mail.channel',
                views: [[false, 'kanban'], [false, 'form']],
                domain: [['public', '!=', 'private']]
            },
        });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onHideAddingItem(ev) {
        ev.stopPropagation();
        this.discuss.clearIsAddingItem();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onInputQuickSearch(ev) {
        this.discuss.onInputQuickSearch(ev.target.value);
    }

}

Object.assign(DiscussSidebar, {
    components,
    props: {},
    template: 'mail.DiscussSidebar',
});
