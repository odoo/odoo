/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerTextInput extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'textInputComponent', modelName: 'ComposerView' });
        useRefToModel({ fieldName: 'mirroredTextareaRef', modelName: 'ComposerView', refName: 'mirroredTextarea' });
        useRefToModel({ fieldName: 'textareaRef', modelName: 'ComposerView', refName: 'textarea' });
        /**
         * Updates the composer text input content when composer is mounted
         * as textarea content can't be changed from the DOM.
         */
        useUpdate({ func: () => this._update() });
        /**
         * Last content of textarea from input event. Useful to determine
         * whether the current partner is typing something.
         */
        this._textareaLastInputValue = "";
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerView}
     */
    get composerView() {
        return this.messaging && this.messaging.models['ComposerView'].get(this.props.localId);
    }

    /**
     * Saves the composer text input state in store
     */
    saveStateInStore() {
        this.composerView.composer.update({
            textInputContent: this._getContent(),
            textInputCursorEnd: this._getSelectionEnd(),
            textInputCursorStart: this.composerView.textareaRef.el.selectionStart,
            textInputSelectionDirection: this.composerView.textareaRef.el.selectionDirection,
        });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns textarea current content.
     *
     * @private
     * @returns {string}
     */
    _getContent() {
        return this.composerView.textareaRef.el.value;
    }

    /**
     * Returns selection end position.
     *
     * @private
     * @returns {integer}
     */
    _getSelectionEnd() {
        return this.composerView.textareaRef.el.selectionEnd;
    }

    /**
     * Determines whether the textarea is empty or not.
     *
     * @private
     * @returns {boolean}
     */
    _isEmpty() {
        return this._getContent() === "";
    }

    /**
     * Updates the content and height of a textarea
     *
     * @private
     */
    _update() {
        if (!this.composerView) {
            return;
        }
        if (!this.root.el) {
            return;
        }
        if (this.composerView.doFocus) {
            this.composerView.update({ doFocus: false });
            if (this.messaging.device.isMobile) {
                this.root.el.scrollIntoView();
            }
            this.composerView.textareaRef.el.focus();
        }
        if (this.composerView.hasToRestoreContent) {
            this.composerView.textareaRef.el.value = this.composerView.composer.textInputContent;
            if (this.composerView.isFocused) {
                this.composerView.textareaRef.el.setSelectionRange(
                    this.composerView.composer.textInputCursorStart,
                    this.composerView.composer.textInputCursorEnd,
                    this.composerView.composer.textInputSelectionDirection,
                );
            }
            this.composerView.update({ hasToRestoreContent: false });
        }
        this._updateHeight();
    }

    /**
     * Updates the textarea height.
     *
     * @private
     */
    _updateHeight() {
        this.composerView.mirroredTextareaRef.el.value = this.composerView.composer.textInputContent;
        this.composerView.textareaRef.el.style.height = this.composerView.mirroredTextareaRef.el.scrollHeight + 'px';
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickTextarea() {
        if (!this.composerView) {
            return;
        }
        // clicking might change the cursor position
        this.saveStateInStore();
    }

    /**
     * @private
     */
    _onFocusoutTextarea() {
        if (!this.composerView) {
            return;
        }
        this.saveStateInStore();
        this.composerView.update({ isFocused: false });
    }

    /**
     * @private
     */
    _onInputTextarea() {
        if (!this.composerView) {
            return;
        }
        this.saveStateInStore();
        if (this._textareaLastInputValue !== this.composerView.textareaRef.el.value) {
            this.composerView.handleCurrentPartnerIsTyping();
        }
        this._textareaLastInputValue = this.composerView.textareaRef.el.value;
        this._updateHeight();
    }

    /**
     * Key events management is performed in a Keyup to avoid intempestive RPC calls
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeyupTextarea(ev) {
        if (!this.composerView) {
            return;
        }
        switch (ev.key) {
            case 'Escape':
                // already handled in _onKeydownTextarea, break to avoid default
                break;
            // ENTER, HOME, END, UP, DOWN, PAGE UP, PAGE DOWN, TAB: check if navigation in mention suggestions
            case 'Enter':
                if (this.composerView.hasSuggestions) {
                    this.composerView.insertSuggestion();
                    this.composerView.closeSuggestions();
                    this.composerView.update({ doFocus: true });
                }
                break;
            case 'ArrowUp':
            case 'PageUp':
                if (ev.key === 'ArrowUp' && !this.composerView.hasSuggestions && !this.composerView.composer.textInputContent && this.composerView.threadView) {
                    this.composerView.threadView.startEditingLastMessageFromCurrentUser();
                    break;
                }
                if (this.composerView.hasSuggestions) {
                    this.composerView.setPreviousSuggestionActive();
                    this.composerView.update({ hasToScrollToActiveSuggestion: true });
                }
                break;
            case 'ArrowDown':
            case 'PageDown':
                if (ev.key === 'ArrowDown' && !this.composerView.hasSuggestions && !this.composerView.composer.textInputContent && this.composerView.threadView) {
                    this.composerView.threadView.startEditingLastMessageFromCurrentUser();
                    break;
                }
                if (this.composerView.hasSuggestions) {
                    this.composerView.setNextSuggestionActive();
                    this.composerView.update({ hasToScrollToActiveSuggestion: true });
                }
                break;
            case 'Home':
                if (this.composerView.hasSuggestions) {
                    this.composerView.setFirstSuggestionActive();
                    this.composerView.update({ hasToScrollToActiveSuggestion: true });
                }
                break;
            case 'End':
                if (this.composerView.hasSuggestions) {
                    this.composerView.setLastSuggestionActive();
                    this.composerView.update({ hasToScrollToActiveSuggestion: true });
                }
                break;
            case 'Tab':
                if (this.composerView.hasSuggestions) {
                    if (ev.shiftKey) {
                        this.composerView.setPreviousSuggestionActive();
                        this.composerView.update({ hasToScrollToActiveSuggestion: true });
                    } else {
                        this.composerView.setNextSuggestionActive();
                        this.composerView.update({ hasToScrollToActiveSuggestion: true });
                    }
                }
                break;
            case 'Alt':
            case 'AltGraph':
            case 'CapsLock':
            case 'Control':
            case 'Fn':
            case 'FnLock':
            case 'Hyper':
            case 'Meta':
            case 'NumLock':
            case 'ScrollLock':
            case 'Shift':
            case 'ShiftSuper':
            case 'Symbol':
            case 'SymbolLock':
                // prevent modifier keys from resetting the suggestion state
                break;
            // Otherwise, check if a mention is typed
            default:
                this.saveStateInStore();
        }
    }

}

Object.assign(ComposerTextInput, {
    defaultProps: {
        hasMentionSuggestionsBelowPosition: false,
    },
    props: {
        localId: String,
        hasMentionSuggestionsBelowPosition: {
            type: Boolean,
            optional: true,
        },
    },
    template: 'mail.ComposerTextInput',
});

registerMessagingComponent(ComposerTextInput);
