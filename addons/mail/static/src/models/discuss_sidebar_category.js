/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'DiscussSidebarCategory',
    identifyingMode: 'xor',
    modelMethods: {
        /**
         * Performs the `set_res_users_settings` RPC on `res.users.settings`.
         *
         * @param {Object} resUsersSettings
         * @param {boolean} [resUsersSettings.is_category_channel_open]
         * @param {boolean} [resUsersSettings.is_category_chat_open]
         */
        async performRpcSetResUsersSettings(resUsersSettings) {
            return this.messaging.rpc(
                {
                    model: 'res.users.settings',
                    method: 'set_res_users_settings',
                    args: [[this.messaging.currentUser.res_users_settings_id.id]],
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
         * @returns {FieldCommand}
         */
        _computeActiveItem() {
            const channel = this.messaging.discuss.activeThread && this.messaging.discuss.activeThread.channel;
            if (channel && this.supportedChannelTypes.includes(channel.channel_type)) {
                return {
                    thread: channel.thread,
                    category: this,
                };
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAddingItemAutocompleteInputView() {
            if (this.isOpen && this.isAddingItem) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeAutocompleteMethod() {
            if (this.discussAsChannel) {
                return 'channel';
            }
            if (this.discussAsChat) {
                return 'chat';
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeCommandAddTitleText() {
            if (this.discussAsChannel) {
                return this.env._t("Add or join a channel");
            }
            if (this.discussAsChat) {
                return this.env._t("Start a conversation");
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
                    const nameVal = categoryItem.thread.displayName.toLowerCase();
                    return nameVal.includes(qsVal);
                });
            }
            return categoryItems;
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasAddCommand() {
            if (this.discussAsChannel) {
                return true;
            }
            if (this.discussAsChat) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasViewCommand() {
            if (this.discussAsChannel) {
                return true;
            }
            return clear();
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
         * @returns {boolean|FieldCommand}
         */
        _computeIsServerOpen() {
            // there is no server state for non-users (guests)
            if (!this.messaging.currentUser) {
                return clear();
            }
            if (!this.messaging.currentUser.res_users_settings_id) {
                return clear();
            }
            if (this.discussAsChannel) {
                return this.messaging.currentUser.res_users_settings_id.is_discuss_sidebar_category_channel_open;
            }
            if (this.discussAsChat) {
                return this.messaging.currentUser.res_users_settings_id.is_discuss_sidebar_category_chat_open;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeName() {
            if (this.discussAsChannel) {
                return this.env._t("Channels");
            }
            if (this.discussAsChat) {
                return this.env._t("Direct Messages");
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeNewItemPlaceholderText() {
            if (this.discussAsChannel) {
                return this.env._t("Find or create a channel...");
            }
            if (this.discussAsChat) {
                return this.env._t("Find or start a conversation...");
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeServerStateKey() {
            if (this.discussAsChannel) {
                return 'is_discuss_sidebar_category_channel_open';
            }
            if (this.discussAsChat) {
                return 'is_discuss_sidebar_category_chat_open';
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeSortComputeMethod() {
            if (this.discussAsChannel) {
                return 'name';
            }
            if (this.discussAsChat) {
                return 'last_action';
            }
            return clear();
        },
        /**
         * @private
         * @returns {string[]|FieldCommand}
         */
        _computeSupportedChannelTypes() {
            if (this.discussAsChannel) {
                return ['channel'];
            }
            if (this.discussAsChat) {
                return ['chat', 'group'];
            }
            return clear();
        },
        /**
         * @private
         * @returns {Array[]}
         */
        _sortDefinitionCategoryItems() {
            switch (this.sortComputeMethod) {
                case 'name':
                    return [
                        ['truthy-first', 'thread'],
                        ['truthy-first', 'thread.displayName'],
                        ['case-insensitive-asc', 'thread.displayName'],
                        ['smaller-first', 'channel.id'],
                    ];
                case 'last_action':
                    return [
                        ['truthy-first', 'thread'],
                        ['truthy-first', 'thread.lastInterestDateTime'],
                        ['most-recent-first', 'thread.lastInterestDateTime'],
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
        onHideAddingItem() {
            this.update({ isAddingItem: false });
        },
        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        onAddItemAutocompleteSelect(ev, ui) {
            switch (this.autocompleteMethod) {
                case 'channel':
                    this.messaging.discuss.handleAddChannelAutocompleteSelect(ev, ui);
                    break;
                case 'chat':
                    this.messaging.discuss.handleAddChatAutocompleteSelect(ev, ui);
                    break;
            }
        },
        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        onAddItemAutocompleteSource(req, res) {
            switch (this.autocompleteMethod) {
                case 'channel':
                    this.messaging.discuss.handleAddChannelAutocompleteSource(req, res);
                    break;
                case 'chat':
                    this.messaging.discuss.handleAddChatAutocompleteSource(req, res);
                    break;
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickCommandAdd(ev) {
            ev.stopPropagation();
            this.update({ isAddingItem: true });
        },
        /**
         * Redirects to the public channels window when view command is clicked.
         *
         * @param {MouseEvent} ev
         */
        onClickCommandView(ev) {
            ev.stopPropagation();
            return this.env.services.action.doAction({
                name: this.env._t("Public Channels"),
                type: 'ir.actions.act_window',
                res_model: 'mail.channel',
                views: [[false, 'kanban'], [false, 'form']],
                domain: [['public', '!=', 'private']],
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
        addingItemAutocompleteInputView: one('AutocompleteInputView', {
            compute: '_computeAddingItemAutocompleteInputView',
            inverse: 'discussSidebarCategoryOwnerAsAddingItem',
            isCausal: true,
        }),
        /**
         * Determines how the autocomplete of this category should behave.
         * Must be one of: 'channel', 'chat'.
         */
        autocompleteMethod: attr({
            compute: '_computeAutocompleteMethod',
            default: '',
        }),
        /**
         * The title text in UI for command `add`
         */
        commandAddTitleText: attr({
            compute: '_computeCommandAddTitleText',
            default: '',
        }),
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
            identifying: true,
            inverse: 'categoryChannel',
        }),
        discussAsChat: one('Discuss', {
            identifying: true,
            inverse: 'categoryChat',
        }),
        /**
         * Determines the filtered and sorted discuss sidebar category items
         * that are displayed by this discuss sidebar category.
         */
        filteredCategoryItems: many('DiscussSidebarCategoryItem', {
            compute: '_computeFilteredCategoryItems',
        }),
        /**
         * Display name of the category.
         */
        name: attr({
            compute: '_computeName',
            default: '',
        }),
        /**
         * Boolean that determines whether this category has a 'add' command.
         */
        hasAddCommand: attr({
            compute: '_computeHasAddCommand',
            default: false,
        }),
        /**
         * Boolean that determines whether this category has a 'view' command.
         */
        hasViewCommand: attr({
            compute: '_computeHasViewCommand',
            default: false,
        }),
        /**
         * Boolean that determines whether discuss is adding a new category item.
         */
        isAddingItem: attr({
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
        isServerOpen: attr({
            compute: '_computeIsServerOpen',
            default: false,
        }),
        /**
         * The placeholder text used when a new item is being added in UI.
         */
        newItemPlaceholderText: attr({
            compute: '_computeNewItemPlaceholderText',
        }),
        /**
         * The key used in the server side for the category state
         */
        serverStateKey: attr({
            compute: '_computeServerStateKey',
        }),
        /**
         * Determines the sorting method of channels in this category.
         * Must be one of: 'name', 'last_action'.
         */
        sortComputeMethod: attr({
            compute: '_computeSortComputeMethod',
            required: true,
        }),
        /**
         * Channel type which is supported by the category.
         */
        supportedChannelTypes: attr({
            compute: '_computeSupportedChannelTypes',
            required: true,
        }),
    },
    onChanges: [
        {
            dependencies: ['isServerOpen'],
            methodName: '_onIsServerOpenChanged',
        },
    ],
});
