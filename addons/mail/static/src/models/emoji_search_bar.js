/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiSearchBar',
    identifyingFields: ['emojiPickerView'],
    recordMethods: {
        /**
         * Handles OWL update on this EmojiSearchBar component.
         */
        onComponentUpdate() {
            this._handleFocus();
        },
        /**
         * @public
         */
        onInput() {
            if (!this.exists()) {
                return;
            }
            this.saveStateInStore();
        },
        /**
         * @public
         */
        reinitializeSearch() {
            this.update({ currentSearch: "" });
            this.inputRef.el.value = "";
            this.update({ isDoFocus: true });
        },
        /**
         * @public
         */
        saveStateInStore() {
            this.update({
                currentSearch: this.inputRef.el.value,
            });
        },
        /**
         * @private
         */
        _handleFocus() {
            if (this.isDoFocus) {
                if (!this.inputRef.el) {
                    return;
                }
                this.update({ isDoFocus: false });
                this.inputRef.el.focus();
            }
        },
    },
    fields: {
        currentSearch: attr({
            default: "",
        }),
        emojiPickerView: one("EmojiPickerView", {
            inverse: "emojiSearchBar",
            readonly: true,
            required: true,
        }),
        inputRef: attr(),
        isDoFocus: attr({
            default: true,
        }),
        placeholder: attr({
            default: "Search here to find an emoji",
            readonly: true,
            required: true,
        }),
    },
});
