/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'AutocompleteInputView',
    identifyingFields: [[
        'chatWindowOwnerAsNewMessageFormInput',
        'discussViewOwnerAsMobileAddChannel',
        'discussViewOwnerAsMobileAddChat',
        'discussViewOwnerAsSidebarAddChannel',
        'discussViewOwnerAsSidebarAddChat',
        'messagingMenuOwnerAsMobileNewMessageInput',
    ]],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        async onBlur(ev) {
            if (!this.messaging) {
                return;
            }
            /**
             * Wait a tick for handling of "click" event
             * So that "click" happens before "blur".
             * (In Web API, "blur" has precendence over "click")
             * So if click acts as a toggle, this blur will be silently ignored.
             */
            await new Promise(this.messaging.browser.setTimeout);
            if (!this.exists()) {
                return;
            }
            if (this.chatWindowOwnerAsNewMessageFormInput) {
                return;
            }
            this.delete();
        },
        onComponentUpdate() {
            if (this.doFocus) {
                this.component.root.el.focus();
                this.update({ doFocus: false });
            }
        },
        onFocusin() {
            if (!this.exists()) {
                return;
            }
            this.update({ isFocused: true });
        },
        /**
         * @param {MouseEvent} ev
         */
        onKeydown(ev) {
            if (this.chatWindowOwnerAsNewMessageFormInput) {
                return;
            }
            if (ev.key === 'Escape') {
                this.delete();
            }
        },
        /**
         * Called when selecting an item in this autocomplete input view
         *
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        async onSelect(ev, ui) {
            if (
                this.discussViewOwnerAsSidebarAddChannel ||
                this.discussViewOwnerAsMobileAddChannel
            ) {
                this._onSelectChannel(ev, ui);
            }
            if (
                this.discussViewOwnerAsSidebarAddChat ||
                this.discussViewOwnerAsMobileAddChat ||
                this.messagingMenuOwnerAsMobileNewMessageInput
            ) {
                this._onSelectChat(ev, ui);
            }
            if (this.chatWindowOwnerAsNewMessageFormInput) {
                const chat = await this.messaging.getChat({ partnerId: ui.item.id });
                if (!chat) {
                    return;
                }
                this.messaging.chatWindowManager.openThread(chat, {
                    makeActive: true,
                    replaceNewMessage: true,
                });
            }
        },
        /**
         * Called when typing in this autocomplete input view.
         *
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        onSource(req, res) {
            if (
                this.chatWindowOwnerAsNewMessageFormInput ||
                this.discussViewOwnerAsSidebarAddChat ||
                this.discussViewOwnerAsMobileAddChat ||
                this.messagingMenuOwnerAsMobileNewMessageInput
            ) {
                this._onSourceChat(req, res);
            }
            if (
                this.discussViewOwnerAsSidebarAddChannel ||
                this.discussViewOwnerAsMobileAddChannel
            ) {
                this._onSourceChannel(req, res);
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeCustomClass() {
            return 'o_AutocompleteInputView_customClass';
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsHtml() {
            if (
                this.discussViewOwnerAsSidebarAddChannel ||
                this.discussViewOwnerAsMobileAddChannel
            ) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computePlaceholder() {
            if (
                this.chatWindowOwnerAsNewMessageFormInput ||
                this.discussViewOwnerAsMobileAddChat ||
                this.messagingMenuOwnerAsMobileNewMessageInput
            ) {
                return this.env._t("Search user...");
            }
            if (this.discussViewOwnerAsMobileAddChannel) {
                return this.env._t("Create or search channel...");
            }
            if (this.discussViewOwnerAsSidebarAddChannel) {
                return this.env._t("Find or create a channel...");
            }
            if (this.discussViewOwnerAsSidebarAddChat) {
                return this.env._t("Find or start a conversation...");
            }
            return clear();
        },
        /**
         * @private
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        async _onSelectChannel(ev, ui) {
            if (ui.item.special) {
                const channel = await this.async(() =>
                    this.messaging.models['Thread'].performRpcCreateChannel({
                        name: this.inputValue,
                        privacy: ui.item.special,
                    })
                );
                channel.open();
            } else {
                const channel = this.messaging.models['Thread'].insert({
                    id: ui.item.id,
                    model: 'mail.channel',
                });
                await channel.join();
                // Channel must be pinned immediately to be able to open it before
                // the result of join is received on the bus.
                channel.update({ isServerPinned: true });
                channel.open();
            }
            this.delete();
        },
        /**
         * @private
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        _onSelectChat(ev, ui) {
            this.messaging.openChat({ partnerId: ui.item.id });
            if (!this.messagingMenuOwnerAsMobileNewMessageInput) {
                this.delete();
            }
        },
        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        async _onSourceChannel(req, res) {
            this.update({ inputValue: req.term });
            const threads = await this.messaging.models['Thread'].searchChannelsToOpen({ limit: 10, searchTerm: req.term });
            const items = threads.map((thread) => {
                const escapedName = escape(thread.name);
                return {
                    id: thread.id,
                    label: escapedName,
                    value: escapedName,
                };
            });
            const escapedValue = escape(req.term);
            // XDU FIXME could use a component but be careful with owl's
            // renderToString https://github.com/odoo/owl/issues/708
            items.push({
                label: _.str.sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-hashtag"/>${escapedValue}</em>`,
                ),
                escapedValue,
                special: 'public'
            }, {
                label: _.str.sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-lock"/>${escapedValue}</em>`,
                ),
                escapedValue,
                special: 'private'
            });
            res(items);
        },
        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        async _onSourceChat(req, res) {
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
                keyword: req.term,
                limit: 10,
            });
        },
    },
    fields: {
        chatWindowOwnerAsNewMessageFormInput: one('ChatWindow', {
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
        discussViewOwnerAsMobileAddChannel: one('DiscussView', {
            inverse: 'mobileAddChannelInputView',
            readonly: true,
        }),
        discussViewOwnerAsMobileAddChat: one('DiscussView', {
            inverse: 'mobileAddChatInputView',
            readonly: true,
        }),
        discussViewOwnerAsSidebarAddChannel: one('DiscussView', {
            inverse: 'sidebarAddChannelInputView',
            readonly: true,
        }),
        discussViewOwnerAsSidebarAddChat: one('DiscussView', {
            inverse: 'sidebarAddChatInputView',
            readonly: true,
        }),
        doFocus: attr({
            default: false,
        }),
        /**
         * Value inside the input of this autocomplete input view.
         */
        inputValue: attr({
            default: '',
        }),
        isFocused: attr({
            default: false,
        }),
        /**
         * When this is true, make sure onSource is properly escaped.
         */
        isHtml: attr({
            compute: '_computeIsHtml',
            default: false,
        }),
        messagingMenuOwnerAsMobileNewMessageInput: one('MessagingMenu', {
            inverse: 'mobileNewMessageInputView',
            readonly: true,
        }),
        placeholder: attr({
            compute: '_computePlaceholder',
            default: '',
        }),
    },
});
