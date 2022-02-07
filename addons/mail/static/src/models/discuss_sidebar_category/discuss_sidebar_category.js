/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'DiscussSidebarCategory',
    identifyingFields: [['discussAsChannel', 'discussAsChat']],
    modelMethods: {
        /**
         * Performs the `set_res_users_settings` RPC on `res.users.settings`.
         *
         * @param {Object} resUsersSettings
         * @param {boolean} [resUsersSettings.is_category_channel_open]
         * @param {boolean} [resUsersSettings.is_category_chat_open]
         */
        async performRpcSetResUsersSettings(resUsersSettings) {
            return this.env.services.rpc(
                {
                    model: 'res.users.settings',
                    method: 'set_res_users_settings',
                    args: [[this.messaging.currentUser.resUsersSettingsId]],
                    kwargs: {
                        new_settings: resUsersSettings,
                    },
                },
                { shadow: true },
            );
        },
    },
    recordMethods: {
        /**
         * Closes the category and notity server to change the state
         */
        async close() {
            this.update({ isPendingOpen: false });
            await this.messaging.models['DiscussSidebarCategory'].performRpcSetResUsersSettings({
                [this.serverStateKey]: false,
            });
        },
        /**
         * Opens the category and notity server to change the state
         */
        async open() {
            this.update({ isPendingOpen: true });
            await this.messaging.models['DiscussSidebarCategory'].performRpcSetResUsersSettings({
                [this.serverStateKey]: true,
            });
        },
        /**
         * @private
         * @returns {DiscussSidebarCategoryItem|undefined}
         */
        _computeActiveItem() {
            const thread = this.messaging.discuss.thread;
            if (thread && this.supportedChannelTypes.includes(thread.channel_type)) {
                return insertAndReplace({
                    channel: replace(thread),
                    category: replace(this),
                });
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAddingItemInputView() {
            if (
                this.discussAsChannel &&
                this.messaging.discuss.discussView &&
                this.messaging.discuss.discussView.sidebarAddChannelInputView
            ) {
                return replace(this.messaging.discuss.discussView.sidebarAddChannelInputView);
            }
            if (
                this.discussAsChat &&
                this.messaging.discuss.discussView &&
                this.messaging.discuss.discussView.sidebarAddChatInputView
            ) {
                return replace(this.messaging.discuss.discussView.sidebarAddChatInputView);
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeFilteredCategoryItems() {
            let categoryItems = this.categoryItems;
            const searchValue = this.messaging.discuss.sidebarQuickSearchValue;
            if (searchValue) {
                const qsVal = searchValue.toLowerCase();
                categoryItems = categoryItems.filter(categoryItem => {
                    const nameVal = categoryItem.channel.displayName.toLowerCase();
                    return nameVal.includes(qsVal);
                });
            }
            return replace(categoryItems);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsOpen() {
            return this.isPendingOpen !== undefined ? this.isPendingOpen : this.isServerOpen;
        },
        /**
         * @private
         * @returns {Array[]}
         */
        _sortDefinitionCategoryItems() {
            switch (this.sortComputeMethod) {
                case 'name':
                    return [
                        ['defined-first', 'channel'],
                        ['defined-first', 'channel.displayName'],
                        ['case-insensitive-asc', 'channel.displayName'],
                        ['smaller-first', 'channel.id'],
                    ];
                case 'last_action':
                    return [
                        ['defined-first', 'channel'],
                        ['defined-first', 'channel.lastInterestDateTime'],
                        ['greater-first', 'channel.lastInterestDateTime'],
                        ['greater-first', 'channel.id'],
                    ];
            }
        },
        /**
         * Changes the category open states when clicked.
         */
        async onClick() {
            if (this.isOpen) {
                await this.close();
            } else {
                await this.open();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickCommandAdd(ev) {
            ev.stopPropagation();
            if (this.discussAsChannel) {
                this.messaging.discuss.discussView.update({ sidebarAddChannelInputView: insertAndReplace({ doFocus: true }) });
            }
            if (this.discussAsChat) {
                this.messaging.discuss.discussView.update({ sidebarAddChatInputView: insertAndReplace({ doFocus: true }) });
            }
        },
        /**
         * Redirects to the public channels window when view command is clicked.
         *
         * @param {MouseEvent} ev
         */
        onClickCommandView(ev) {
            ev.stopPropagation();
            return this.env.bus.trigger('do-action', {
                action: {
                    name: this.env._t("Public Channels"),
                    type: 'ir.actions.act_window',
                    res_model: 'mail.channel',
                    views: [[false, 'kanban'], [false, 'form']],
                    domain: [['public', '!=', 'private']],
                },
            });
        },
        /**
         * Handles change of open state coming from the server. Useful to
         * clear pending state once server acknowledged the change.
         *
         * @private
         */
        _onIsServerOpenChanged() {
            if (this.isServerOpen === this.isPendingOpen) {
                this.update({ isPendingOpen: clear() });
            }
        },
    },
    fields: {
        /**
         * The category item which is active and belongs
         * to the category.
         */
        activeItem: one('DiscussSidebarCategoryItem', {
            compute: '_computeActiveItem',
        }),
        addingItemInputView: one('AutocompleteInputView', {
            compute: '_computeAddingItemInputView',
        }),
        /**
         * Determines how the autocomplete of this category should behave.
         * Must be one of: 'channel', 'chat'.
         */
        autocompleteMethod: attr(),
        /**
         * The title text in UI for command `add`
         */
        commandAddTitleText: attr(),
        /**
         * Determines the discuss sidebar category items that are displayed by
         * this discuss sidebar category.
         */
        categoryItems: many('DiscussSidebarCategoryItem', {
            inverse: 'category',
            isCausal: true,
            sort: '_sortDefinitionCategoryItems',
        }),
        /**
         * States the total amount of unread/action-needed threads in this
         * category.
         */
        counter: attr({
            default: 0,
            readonly: true,
            sum: 'categoryItems.categoryCounterContribution',
        }),
        discussAsChannel: one('Discuss', {
            inverse: 'categoryChannel',
            readonly: true,
        }),
        discussAsChat: one('Discuss', {
            inverse: 'categoryChat',
            readonly: true,
        }),
        /**
         * Determines the filtered and sorted discuss sidebar category items
         * that are displayed by this discuss sidebar category.
         */
        filteredCategoryItems: many('DiscussSidebarCategoryItem', {
            compute: '_computeFilteredCategoryItems',
            readonly: true,
        }),
        /**
         * Display name of the category.
         */
        name: attr(),
        /**
         * Boolean that determines whether this category has a 'add' command.
         */
        hasAddCommand: attr({
            default: false,
        }),
        /**
         * Boolean that determines whether this category has a 'view' command.
         */
        hasViewCommand: attr({
            default: false,
        }),
        /**
         * Boolean that determines whether this category is open.
         */
        isOpen: attr({
            compute: '_computeIsOpen',
        }),
        /**
         * Boolean that determines if there is a pending open state change,
         * which is requested by the client but not yet confirmed by the server.
         *
         * This field can be updated to immediately change the open state on the
         * interface and to notify the server of the new state.
         */
        isPendingOpen: attr(),
        /**
         * Boolean that determines the last open state known by the server.
         */
        isServerOpen: attr(),
        /**
         * The key used in the server side for the category state
         */
        serverStateKey: attr({
            readonly: true,
            required: true,
        }),
        /**
         * Determines the sorting method of channels in this category.
         * Must be one of: 'name', 'last_action'.
         */
        sortComputeMethod: attr({
            required: true,
        }),
        /**
         * Channel type which is supported by the category.
         */
        supportedChannelTypes: attr({
            required: true,
            readonly: true,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['isServerOpen'],
            methodName: ['_onIsServerOpenChanged'],
        }),
    ],
});
