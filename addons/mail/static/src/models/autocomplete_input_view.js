/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'AutocompleteInputView',
    identifyingFields: ['chatWindowOwnerAsNewMessageFormInput'],
    lifecycleHooks: {
        _created() {
            document.addEventListener('click', this._onClickCaptureGlobal, true);
        },
        _willDelete() {
            document.removeEventListener('click', this._onClickCaptureGlobal, true);
        },
    },
    recordMethods: {
        onComponentUpdate() {
            if (this.doFocus) {
                this.component.root.el.focus();
                this.update({ doFocus: false });
            }
        },
        onCompositionstart() {
            this.update({ isComposing: true });
        },
        onCompositionend() {
            this.update({ isComposing: false });
            if (this.inputRef.el.value !== this.content) {
                this.update({
                    content: this.inputRef.el.value,
                    width: this.inputRef.el.offsetWidth,
                });
                this._updateSuggestedPartners();
            }
        },
        onFocusin() {
            if (!this.exists()) {
                return;
            }
            this.update({ isFocused: true });
        },
        /**
         * @param {InputEvent} ev 
         */
        onInput(ev) {
            if (!this.exists()) {
                return;
            }
            if (!this.isComposing && this.inputRef.el.value !== this.content) {
                this.update({
                    content: this.inputRef.el.value,
                    width: this.inputRef.el.offsetWidth,
                });
                this._updateSuggestedPartners();
            }
        },
        /**
         * @param {KeyboardEvent} ev
         */
        onKeydown(ev) {
            if (!this.exists()) {
                return;
            }
            if (!this.suggestionPopoverView) {
                return;
            }
            if (this.isComposing) {
                return;
            }
            if (ev.key === 'Escape' && !this.chatWindowOwnerAsNewMessageFormInput) {
                this.delete();
                return;
            }
            if (ev.key === 'Enter') {
                this.suggestionPopoverView.autocompleteInputSuggestionView.activeItemView.select();
                ev.preventDefault();
                return;
            }
            if (['ArrowUp', 'PageUp'].includes(ev.key)) {
                this.suggestionPopoverView.autocompleteInputSuggestionView.changeActivePrevious();
                ev.preventDefault();
                return;
            }
            if (['ArrowDown', 'PageDown'].includes(ev.key)) {
                this.suggestionPopoverView.autocompleteInputSuggestionView.changeActiveNext();
                ev.preventDefault();
                return;
            }
            if (ev.key === 'Home') {
                this.suggestionPopoverView.autocompleteInputSuggestionView.changeActiveFirst();
                ev.preventDefault();
                return;
            }
            if (ev.key === 'End') {
                this.suggestionPopoverView.autocompleteInputSuggestionView.changeActiveLast();
                ev.preventDefault();
                return;
            }
            if (ev.key === 'Tab' && ev.shiftKey) {
                this.suggestionPopoverView.autocompleteInputSuggestionView.changeActivePrevious();
                ev.preventDefault();
                return;
            }
            if (ev.key === 'Tab' && !ev.shiftKey) {
                this.suggestionPopoverView.autocompleteInputSuggestionView.changeActiveNext();
                ev.preventDefault();
                return;
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
         * @private
         * @returns {FieldCommand}
         */
        _computeSuggestionPopoverView() {
            if (this.suggestedPartners.length > 0 && this.isFocused) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * Closes the popover when clicking outside, if appropriate.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (!this.exists()) {
                return;
            }
            if (!this.component || !this.component.root.el) {
                return;
            }
            if (this.component.root.el.contains(ev.target)) {
                this.update({ isFocused: true });
                return;
            }
            if (this.suggestionPopoverView && this.suggestionPopoverView.contains(ev.target)) {
                this.update({ isFocused: true });
                return;
            }
            if (this.component.root.el === document.activeElement) {
                this.update({ isFocused: true });
                return;
            }
            this.update({ isFocused: false });
        },
        /**
         * @private
         */
        _updateSuggestedPartners() {
            this.messaging.models['Partner'].imSearch({
                callback: (partners) => {
                    if (!this.content) {
                        this.update({ suggestedPartners: clear() });
                    } else {
                        const suggestedPartners = _.sortBy(partners, 'nameOrDisplayName');
                        this.update({ suggestedPartners: replace(suggestedPartners) });
                    }
                },
                keyword: this.content,
                limit: 10,
            });
        },
    },
    fields: {
        chatWindowOwnerAsNewMessageFormInput: one('ChatWindow', {
            inverse: 'newMessageFormInputView',
            readonly: true,
        }),
        suggestionPopoverView: one('PopoverView', {
            compute: '_computeSuggestionPopoverView',
            inverse: 'autocompleteInputViewOwner',
            isCausal: true,
        }),
        /**
         * States the OWL component of this autocomplete input view.
         */
        component: attr(),
        content: attr(),
        customClass: attr({
            default: '',
        }),
        doFocus: attr({
            default: false,
        }),
        /**
         * OWL Ref of the <input> of this autocomplete input view.
         */
        inputRef: attr(),
        isComposing: attr({
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
        suggestedPartners: many('Partner'),
        width: attr({
            default: undefined,
        }),
    },
});
