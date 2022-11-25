/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiSearchBarView',
    lifecycleHooks: {
        _created() {
            if (!this.messaging.device.isSmall) {
                this.update({ isDoFocus: true });
            }
        }
    },
    recordMethods: {
        /**
         * Handles OWL update on this EmojiSearchBarView component.
         */
        onComponentUpdate() {
            this._handleFocus();
        },
        onFocusinInput() {
            if (!this.exists()) {
                return;
            }
            this.update({ isFocused: true });
        },
        onFocusoutInput() {
            if (!this.exists()) {
                return;
            }
            this.update({ isFocused: false });
        },
        /**
         * @public
         */
        onInput() {
            if (!this.exists()) {
                return;
            }
            this.update({
                currentSearch: this.inputRef.el.value,
            });
        },
        /**
         * @public
         */
        reset() {
            this.update({ currentSearch: "" });
            this.inputRef.el.value = "";
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
            identifying: true,
            inverse: "emojiSearchBarView",
        }),
        inputRef: attr(),
        isDoFocus: attr({
            default: false,
        }),
        isFocused: attr({
            default: false,
        }),
        placeholder: attr({
            compute() {
                return this.env._t("Search an emoji");
            },
            required: true,
        }),
    },
});
