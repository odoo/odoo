/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'AutocompleteInputView',
    identifyingFields: ['chatWindowOwnerAsNewMessageFormInput'],
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
            if (this.chatWindowOwnerAsNewMessageFormInput) {
                this._onSourceChat(req, res);
            }
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computePlaceholder() {
            if (this.chatWindowOwnerAsNewMessageFormInput) {
                return this.env._t("Search user...");
            }
            return clear();
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
            default: '',
        }),
        doFocus: attr({
            default: false,
        }),
        isFocused: attr({
            default: false,
        }),
        /**
         * When this is true, make sure onSource is properly escaped.
         */
        isHtml: attr({
            default: false,
        }),
        placeholder: attr({
            compute: '_computePlaceholder',
            default: '',
        }),
    },
});
