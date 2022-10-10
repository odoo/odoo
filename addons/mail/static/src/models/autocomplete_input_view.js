/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { escape } from '@web/core/utils/strings';

registerModel({
    name: 'AutocompleteInputView',
    identifyingMode: 'xor',
    lifecycleHooks: {
        _created() {
            document.addEventListener('click', this.onClickCaptureGlobal, true);
        },
        _willDelete() {
            document.removeEventListener('click', this.onClickCaptureGlobal, true);
        },
    },
    recordMethods: {
        /**
         * Returns whether the given html element is inside this autocompleteInput view,
         * including whether it's inside the suggestion list when active.
         * @param {Element} element
         * @returns {boolean}
         */
        contains(element) {
            if (this.autocompleteInputSuggestionListView && this.autocompleteInputSuggestionListView.contains(element)) {
                return true;
            }
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        hide() {
            if (!this.exists()) {
                return;
            }
            if (this.discussSidebarCategoryOwnerAsAddingItem) {
                this.discussSidebarCategoryOwnerAsAddingItem.onHideAddingItem();
                return;
            }
            if (this.discussViewOwnerAsMobileAddItemHeader) {
                this.discussViewOwnerAsMobileAddItemHeader.onHideMobileAddItemHeader();
                return;
            }
            if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                this.messagingMenuOwnerAsMobileNewMessageInput.onHideMobileNewMessage();
                return;
            }
        },
        /**
         * @param {FocusEvent} ev
         */
        onFocusin(ev) {
            if (!this.exists()) {
                return;
            }
            if (this.chatWindowOwnerAsNewMessage) {
                this.chatWindowOwnerAsNewMessage.onFocusInNewMessageFormInput(ev);
                return;
            }
        },
        onClickCaptureGlobal(ev) {
            if (this.contains(ev.target)) {
                return;
            }
            this.hide();
        },
        async onInputSearch(ev) {
            if (!this.exists()) {
                return;
            }
            this.update({ searchTerm: escape(ev.target.value) });
            if (!this.searchTerm) {
                this.update({ suggestions: clear() });
                return;
            }
            if (
                this.chatWindowOwnerAsNewMessage ||
                this.discussSidebarCategoryOwnerAsAddingItem && this.discussSidebarCategoryOwnerAsAddingItem.discussAsChat ||
                this.discussViewOwnerAsMobileAddItemHeader && this.discussViewOwnerAsMobileAddItemHeader.isAddingChat ||
                this.messagingMenuOwnerAsMobileNewMessageInput
            ) {
                this.searchPartnersToInvite().then(suggestions => this.update({ suggestions: suggestions }));
            } else if (
                this.discussSidebarCategoryOwnerAsAddingItem && this.discussSidebarCategoryOwnerAsAddingItem.discussAsChannel ||
                this.discussViewOwnerAsMobileAddItemHeader && this.discussViewOwnerAsMobileAddItemHeader.isAddingChannel
            ) {
                this.searchChannelsToJoin().then(suggestions => {
                    if (this.creatingChannelSuggestable) {
                        suggestions.push({
                            ownerAsCreatingChannel: this,
                        });
                    }
                    this.update({ suggestions: suggestions });
                });
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        async onKeydown(ev) {
            if (!this.exists()) {
                return;
            }
            switch (ev.key) {
                case 'ArrowUp':
                case 'PageUp':
                    if (this.autocompleteInputSuggestionListView) {
                        // prevent moving cursor if navigation in mention suggestions
                        ev.preventDefault();
                        this.autocompleteInputSuggestionListView.setPreviousSuggestionViewActive();
                    }
                    break;
                case 'ArrowDown':
                case 'PageDown':
                    if (this.autocompleteInputSuggestionListView) {
                        // prevent moving cursor if navigation in mention suggestions
                        ev.preventDefault();
                        this.autocompleteInputSuggestionListView.setNextSuggestionViewActive();
                    }
                    break;
                case 'Enter':
                    if (this.autocompleteInputSuggestionListView) {
                        await this.autocompleteInputSuggestionListView.activeSuggestionView.onClick();
                    }
                    break;
                case 'Escape':
                    this.hide();
                    break;
            }
        },
        async searchPartnersToInvite() {
            await this.messaging.models['Partner'].imSearch({
                callback: (partners) => {
                    const suggestions = partners.map(partner => { return { partner: partner } });
                    this.update({ suggestions: suggestions });
                },
                keyword: _.escape(this.searchTerm),
                limit: 10,
            });
        },
        async searchChannelsToJoin() {
            const threads = await this.messaging.models['Thread'].searchChannelsToOpen({ limit: 10, searchTerm: this.searchTerm });
            return threads.map((thread) => { return { channel: thread.channel } });
        },
    },
    fields: {
        autocompleteInputSuggestionListView: one('AutocompleteInputSuggestionListView', {
            compute() {
                if (this.suggestions.length > 0) {
                    return {};
                }
                return clear();
            },
            inverse: 'owner',
        }),
        chatWindowOwnerAsNewMessage: one('ChatWindow', {
            identifying: true,
            inverse: 'newMessageAutocompleteInputView',
        }),
        component: attr(),
        customInputClass: attr({
            compute() {
                if (this.chatWindowOwnerAsNewMessage) {
                    return 'flex-grow-1 flex-shrink-1 border';
                }
                if (this.discussViewOwnerAsMobileAddItemHeader) {
                    return 'flex-grow-1 rounded border';
                }
                if (this.discussSidebarCategoryOwnerAsAddingItem) {
                    return 'rounded';
                }
                if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                    return 'rounded-3';
                }
            },
        }),
        creatingChannelSuggestable: one('AutocompleteInputSuggestable', {
            compute() {
                if (
                    this.searchTerm &&
                    (this.discussSidebarCategoryOwnerAsAddingItem && this.discussSidebarCategoryOwnerAsAddingItem.discussAsChannel) ||
                    (this.discussViewOwnerAsMobileAddItemHeader && this.discussViewOwnerAsMobileAddItemHeader.isAddingChannel)
                ) {
                    return {};
                }
                return clear();
            },
            inverse: 'ownerAsCreatingChannel',
        }),
        discussSidebarCategoryOwnerAsAddingItem: one('DiscussSidebarCategory', {
            identifying: true,
            inverse: 'addingItemAutocompleteInputView',
        }),
        discussViewOwnerAsMobileAddItemHeader: one('DiscussView', {
            identifying: true,
            inverse: 'mobileAddItemHeaderAutocompleteInputView',
        }),
        isFocusOnMount: attr({
            compute() {
                if (this.discussViewOwnerAsMobileAddItemHeader) {
                    return true;
                }
                if (this.discussSidebarCategoryOwnerAsAddingItem) {
                    return true;
                }
                if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                    return true;
                }
                return clear();
            },
            default: false,
        }),
        messagingMenuOwnerAsMobileNewMessageInput: one('MessagingMenu', {
            identifying: true,
            inverse: 'mobileNewMessageAutocompleteInputView',
        }),
        placeholder: attr({
            compute() {
                if (this.chatWindowOwnerAsNewMessage) {
                    return this.chatWindowOwnerAsNewMessage.newMessageFormInputPlaceholder;
                }
                if (this.discussViewOwnerAsMobileAddItemHeader) {
                    if (this.discussViewOwnerAsMobileAddItemHeader.isAddingChannel) {
                        return this.discussViewOwnerAsMobileAddItemHeader.discuss.addChannelInputPlaceholder;
                    } else {
                        return this.discussViewOwnerAsMobileAddItemHeader.discuss.addChatInputPlaceholder;
                    }
                }
                if (this.discussSidebarCategoryOwnerAsAddingItem) {
                    return this.discussSidebarCategoryOwnerAsAddingItem.newItemPlaceholderText;
                }
                if (this.messagingMenuOwnerAsMobileNewMessageInput) {
                    return this.messagingMenuOwnerAsMobileNewMessageInput.mobileNewMessageInputPlaceholder;
                }
                return clear();
            },
        }),
        searchTerm: attr({
            default: "",
        }),
        suggestions: many('AutocompleteInputSuggestable'),
    },
});
