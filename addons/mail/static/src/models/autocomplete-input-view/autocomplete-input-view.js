/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'AutocompleteInputView',
    identifyingFields: [['chatWindowOwnerAsNewMessageFormInput', 'discussAsMobileAddItemHeader', 'discussSidebarCategoryAsItemNewInput']],
    lifecycleHooks: {
        _created() {
            this.onBlur = this.onBlur.bind(this);
            this.onFocusin = this.onFocusin.bind(this);
            this.onKeydown = this.onKeydown.bind(this);
        },
    },
    recordMethods: {
        doFocus() {
            if (!this.component) {
                return;
            }
            this.component.root.el.focus();
        },
        /**
         * @param {MouseEvent} ev
         */
        onBlur(ev) {
            this._hide();
        },
        onFocusin() {
            if (this.chatWindowOwnerAsNewMessageFormInput) {
                this.chatWindowOwnerAsNewMessageFormInput({ isFocused: true });
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onKeydown(ev) {
            if (ev.key === 'Escape') {
                this._hide();
            }
        },
        /**
         * @private
         */
        _hide() {
            if (this.discussAsMobileAddItemHeader) {
                this.discussAsMobileAddItemHeader.clearIsAddingItem();
            }
            if (this.discussSidebarCategoryAsItemNewInput) {
                this.discussSidebarCategoryAsItemNewInput.onHideAddingItem();
            }
            if (this.messagingMenuAsMobileNewMessageInput) {
                this.messagingMenuAsMobileNewMessageInput.toggleMobileNewMessage();
            }
        },
        /**
         * @private
         * @returns {boolean/FieldCommand}
         */
        _isFocusOnMount() {
            if (this.discussAsMobileAddItemHeader) {
                return true;
            }
            if (this.discussSidebarCategoryAsItemNewInput) {
                return true;
            }
            if (this.messagingMenuAsMobileNewMessageInput) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeCustomClass() {
            if (this.discussSidebarCategoryAsItemNewInput) {
                if (this.discussSidebarCategoryAsItemNewInput === this.messaging.discuss.categoryChannel) {
                    return 'o_DiscussSidebarCategory_newChannelAutocompleteSuggestions';
                }
            }
            if (this.messagingMenuAsMobileNewMessageInput) {
                return 'o_MessagingMenu_mobileNewMessageInputAutocomplete';
            }
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsHtml() {
            if (this.discussSidebarCategoryAsItemNewInput) {
                return this.discussSidebarCategoryAsItemNewInput === this.messaging.discuss.categoryChannel;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computePlaceholder() {
            if (this.chatWindowOwnerAsNewMessageFormInput) {
                return this.env._t("Search user...");
            }
            if (this.discussAsMobileAddItemHeader) {
                if (this.discussAsMobileAddItemHeader.isAddingChannel) {
                    return this.discussAsMobileAddItemHeader.addChannelInputPlaceholder;
                }
                return this.discussAsMobileAddItemHeader.addChatInputPlaceholder;
            }
            if (this.discussSidebarCategoryAsItemNewInput) {
                return this.discussSidebarCategoryAsItemNewInput.newItemPlaceholderText;
            }
            if (this.messagingMenuAsMobileNewMessageInput) {
                return this.env._t("Search user...");
            }
            return clear();
        },
        /**
         * @private
         * @returns {function|FieldCommand}
         */
        _computeSelect() {
            if (this.chatWindowOwnerAsNewMessageFormInput) {
                /**
                 * Called when selecting an item in the autocomplete input of the
                 * 'new_message' chat window.
                 *
                 * @param {Event} ev
                 * @param {Object} ui
                 * @param {Object} ui.item
                 * @param {integer} ui.item.id
                 */
                return async (ev, ui) => {
                    const chat = await this.messaging.getChat({ partnerId: ui.item.id });
                    if (!chat) {
                        return;
                    }
                    this.messaging.chatWindowManager.openThread(chat, {
                        makeActive: true,
                        replaceNewMessage: true,
                    });
                };
            }
            if (this.discussAsMobileAddItemHeader) {
                /**
                 * @param {Event} ev
                 * @param {Object} ui
                 * @param {Object} ui.item
                 * @param {integer} ui.item.id
                 */
                return (ev, ui) => {
                    if (this.discussAsMobileAddItemHeader.isAddingChannel) {
                        this.discussAsMobileAddItemHeader.handleAddChannelAutocompleteSelect(ev, ui);
                    } else {
                        this.discussAsMobileAddItemHeader.handleAddChatAutocompleteSelect(ev, ui);
                    }
                };
            }
            if (this.discussSidebarCategoryAsItemNewInput) {
                return this.discussSidebarCategoryAsItemNewInput.onAddItemAutocompleteSelect;
            }
            if (this.messagingMenuAsMobileNewMessageInput) {
                /**
                 * @private
                 * @param {Event} ev
                 * @param {Object} ui
                 * @param {Object} ui.item
                 * @param {integer} ui.item.id
                 */
                return (ev, ui) => {
                    this.messaging.openChat({ partnerId: ui.item.id });
                };
            }
            return clear();
        },
        /**
         * @private
         * @returns {function|FieldCommand}
         */
        _computeSource() {
            if (this.chatWindowOwnerAsNewMessageFormInput) {
                /**
                 * Called when typing in the autocomplete input of the 'new_message' chat
                 * window.
                 *
                 * @param {Object} req
                 * @param {string} req.term
                 * @param {function} res
                 */
                return (req, res) => {
                    this.messaging.models['Partner'].imSearch({
                        callback: (partners) => {
                            const suggestions = partners.map(partner => {
                                return {
                                    id: partner.id,
                                    value: partner.nameOrDisplayName,
                                    label: partner.nameOrDisplayName,
                                };
                            });
                            res(_.sortBy(suggestions, 'label'));
                        },
                        keyword: _.escape(req.term),
                        limit: 10,
                    });
                };
            }
            if (this.discussAsMobileAddItemHeader) {
                /**
                 * @param {Object} req
                 * @param {string} req.term
                 * @param {function} res
                 */
                return (req, res) => {
                    if (this.discuss.isAddingChannel) {
                        this.discuss.handleAddChannelAutocompleteSource(req, res);
                    } else {
                        this.discuss.handleAddChatAutocompleteSource(req, res);
                    }
                };
            }
            if (this.discussSidebarCategoryAsItemNewInput) {
                return this.discussSidebarCategoryAsItemNewInput.onAddItemAutocompleteSource;
            }
            if (this.messagingMenuAsMobileNewMessageInput) {
                /**
                 * @param {Object} req
                 * @param {string} req.term
                 * @param {function} res
                 */
                return (req, res) => {
                    const value = _.escape(req.term);
                    this.messaging.models['Partner'].imSearch({
                        callback: partners => {
                            const suggestions = partners.map(partner => {
                                return {
                                    id: partner.id,
                                    value: partner.nameOrDisplayName,
                                    label: partner.nameOrDisplayName,
                                };
                            });
                            res(_.sortBy(suggestions, 'label'));
                        },
                        keyword: value,
                        limit: 10,
                    });
                };
            }
            return clear();
        },
    },
    fields: {
        chatWindowOwnerAsNewMessageFormInput: one2one('ChatWindow', {
            inverse: 'newMessageFormInputView',
            readonly: true,
        }),
        /**
         * States the OWL component of this autocomplete input view.
         */
        component: attr(),
        customClass: attr({
            compute: '_computeCustomClass',
            default: '',
        }),
        discussAsMobileAddItemHeader: one2one('Discuss', {
            inverse: 'mobileAddItemHeaderInputView',
            readonly: true,
        }),
        discussSidebarCategoryAsItemNewInput: one2one('DiscussSidebarCategory', {
            inverse: 'itemNewInputView',
            readonly: true,
        }),
        focus: attr({
            default: () => {},
        }),
        isFocusOnMount: attr({
            compute: '_isFocusOnMount',
            default: false,
        }),
        isHtml: attr({
            compute: '_computeIsHtml',
            default: false,
        }),
        messagingMenuAsMobileNewMessageInput: one2one('MessagingMenu', {
            inverse: 'mobileNewMessageInputView',
            readonly: true,
        }),
        placeholder: attr({
            compute: '_computePlaceholder',
            default: '',
        }),
        select: attr({
            compute: '_computeSelect',
            default: (ev, ui) => {},
        }),
        source: attr({
            compute: '_computeSource',
            default: (req, res) => {},
        }),
    },
});
