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
                domain: [['channel_type', '=', 'channel']],
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
            compute() {
                const channel = this.messaging.discuss.activeThread && this.messaging.discuss.activeThread.channel;
                if (channel && this.supportedChannelTypes.includes(channel.channel_type)) {
                    return {
                        category: this,
                        channel,
                    };
                }
                return clear();
            },
        }),
        addingItemAutocompleteInputView: one('AutocompleteInputView', {
            compute() {
                if (this.isOpen && this.isAddingItem) {
                    return {};
                }
                return clear();
            },
            inverse: 'discussSidebarCategoryOwnerAsAddingItem',
        }),
        /**
         * Determines how the autocomplete of this category should behave.
         * Must be one of: 'channel', 'chat'.
         */
        autocompleteMethod: attr({
            compute() {
                if (this.discussAsChannel) {
                    return 'channel';
                }
                if (this.discussAsChat) {
                    return 'chat';
                }
                return clear();
            },
            default: '',
        }),
        /**
         * Determines the discuss sidebar category items that are displayed by
         * this discuss sidebar category.
         */
        categoryItems: many('DiscussSidebarCategoryItem', {
            inverse: 'category',
        }),
        categoryItemsOrderedByLastAction: many('DiscussSidebarCategoryItem', {
            compute() {
                if (this.discussAsChat) {
                    return this.categoryItems;
                }
                // clear if the value is not going to be used, so that it avoids
                // sorting the items for nothing
                return clear();
            },
            sort: [
                ['truthy-first', 'thread'],
                ['truthy-first', 'thread.lastInterestDateTime'],
                ['most-recent-first', 'thread.lastInterestDateTime'],
                ['greater-first', 'channel.id'],
            ],
        }),
        categoryItemsOrderedByName: many('DiscussSidebarCategoryItem', {
            compute() {
                if (this.discussAsChannel) {
                    return this.categoryItems;
                }
                // clear if the value is not going to be used, so that it avoids
                // sorting the items for nothing
                return clear();
            },
            sort: [
                ['truthy-first', 'thread'],
                ['truthy-first', 'thread.displayName'],
                ['case-insensitive-asc', 'thread.displayName'],
                ['smaller-first', 'channel.id'],
            ],
        }),
        /**
         * The title text in UI for command `add`
         */
        commandAddTitleText: attr({
            compute() {
                if (this.discussAsChannel) {
                    return this.env._t("Add or join a channel");
                }
                if (this.discussAsChat) {
                    return this.env._t("Start a conversation");
                }
                return clear();
            },
            default: '',
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
            compute() {
                let categoryItems = this.orderedCategoryItems;
                const searchValue = this.messaging.discuss.sidebarQuickSearchValue;
                if (searchValue) {
                    const qsVal = searchValue.toLowerCase();
                    categoryItems = categoryItems.filter(categoryItem => {
                        const nameVal = categoryItem.channel.displayName.toLowerCase();
                        return nameVal.includes(qsVal);
                    });
                }
                return categoryItems;
            },
        }),
        /**
         * Display name of the category.
         */
        name: attr({
            compute() {
                if (this.discussAsChannel) {
                    return this.env._t("Channels");
                }
                if (this.discussAsChat) {
                    return this.env._t("Direct Messages");
                }
                return clear();
            },
            default: '',
        }),
        /**
         * Boolean that determines whether this category has a 'add' command.
         */
        hasAddCommand: attr({
            compute() {
                if (this.discussAsChannel) {
                    return true;
                }
                if (this.discussAsChat) {
                    return true;
                }
                return clear();
            },
            default: false,
        }),
        /**
         * Boolean that determines whether this category has a 'view' command.
         */
        hasViewCommand: attr({
            compute() {
                if (this.discussAsChannel) {
                    return true;
                }
                return clear();
            },
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
            compute() {
                return this.isPendingOpen !== undefined ? this.isPendingOpen : this.isServerOpen;
            },
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
            compute() {
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
            default: false,
        }),
        /**
         * The placeholder text used when a new item is being added in UI.
         */
        newItemPlaceholderText: attr({
            compute() {
                if (this.discussAsChannel) {
                    return this.env._t("Find or create a channel...");
                }
                if (this.discussAsChat) {
                    return this.env._t("Find or start a conversation...");
                }
                return clear();
            },
        }),
        orderedCategoryItems: many('DiscussSidebarCategoryItem', {
            compute() {
                if (this.discussAsChannel) {
                    return this.categoryItemsOrderedByName;
                }
                if (this.discussAsChat) {
                    return this.categoryItemsOrderedByLastAction;
                }
                return clear();
            },
        }),
        /**
         * The key used in the server side for the category state
         */
        serverStateKey: attr({
            compute() {
                if (this.discussAsChannel) {
                    return 'is_discuss_sidebar_category_channel_open';
                }
                if (this.discussAsChat) {
                    return 'is_discuss_sidebar_category_chat_open';
                }
                return clear();
            },
        }),
        /**
         * Channel type which is supported by the category.
         */
        supportedChannelTypes: attr({
            compute() {
                if (this.discussAsChannel) {
                    return ['channel'];
                }
                if (this.discussAsChat) {
                    return ['chat', 'group'];
                }
                return clear();
            },
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
