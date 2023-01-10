/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { markEventHandled } from '@mail/utils/utils';

const { Component } = owl;
const { useRef } = owl.hooks;

export class ComposerTextInput extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
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
        /**
         * Reference of the textarea. Useful to set height, selection and content.
         */
        this._textareaRef = useRef('textarea');
        /**
         * This is the invisible textarea used to compute the composer height
         * based on the text content. We need it to downsize the textarea
         * properly without flicker.
         */
        this._mirroredTextareaRef = useRef('mirroredTextarea');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.composer_view}
     */
    get composerView() {
        return this.messaging && this.messaging.models['mail.composer_view'].get(this.props.composerViewLocalId);
    }

    /**
     * @returns {string}
     */
    get textareaPlaceholder() {
        if (!this.composerView) {
            return "";
        }
        if (!this.composerView.composer.thread) {
            return "";
        }
        if (this.composerView.composer.thread.model === 'mail.channel') {
            if (this.composerView.composer.thread.correspondent) {
                return _.str.sprintf(this.env._t("Message %s..."), this.composerView.composer.thread.correspondent.nameOrDisplayName);
            }
            return _.str.sprintf(this.env._t("Message #%s..."), this.composerView.composer.thread.displayName);
        }
        if (this.composerView.composer.isLog) {
            return this.env._t("Log an internal note...");
        }
        return this.env._t("Send a message to followers...");
    }

    /**
     * Saves the composer text input state in store
     */
    saveStateInStore() {
        this.composerView.composer.update({
            textInputContent: this._getContent(),
            textInputCursorEnd: this._getSelectionEnd(),
            textInputCursorStart: this._getSelectionStart(),
            textInputSelectionDirection: this._textareaRef.el.selectionDirection,
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
        return this._textareaRef.el.value;
    }

    /**
     * Returns selection end position.
     *
     * @private
     * @returns {integer}
     */
    _getSelectionEnd() {
        return this._textareaRef.el.selectionEnd;
    }

    /**
     * Returns selection start position.
     *
     * @private
     * @returns {integer}
     *
     */
    _getSelectionStart() {
        return this._textareaRef.el.selectionStart;
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
        if (this.composerView.doFocus) {
            this.composerView.update({ doFocus: false });
            if (this.messaging.device.isMobile) {
                this.el.scrollIntoView();
            }
            this._textareaRef.el.focus();
        }
        if (this.composerView.composer.isLastStateChangeProgrammatic) {
            this._textareaRef.el.value = this.composerView.composer.textInputContent;
            if (this.composerView.hasFocus) {
                this._textareaRef.el.setSelectionRange(
                    this.composerView.composer.textInputCursorStart,
                    this.composerView.composer.textInputCursorEnd,
                    this.composerView.composer.textInputSelectionDirection,
                );
            }
            this.composerView.composer.update({ isLastStateChangeProgrammatic: false });
        }
        this._updateHeight();
    }

    /**
     * Updates the textarea height.
     *
     * @private
     */
    _updateHeight() {
        this._mirroredTextareaRef.el.value = this.composerView.composer.textInputContent;
        this._textareaRef.el.style.height = (this._mirroredTextareaRef.el.scrollHeight) + "px";
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
    _onFocusinTextarea() {
        if (!this.composerView) {
            return;
        }
        this.composerView.update({ hasFocus: true });
    }

    /**
     * @private
     */
    _onFocusoutTextarea() {
        if (!this.composerView) {
            return;
        }
        this.saveStateInStore();
        this.composerView.update({ hasFocus: false });
    }

    /**
     * @private
     */
    _onInputTextarea() {
        if (!this.composerView) {
            return;
        }
        this.saveStateInStore();
        if (this._textareaLastInputValue !== this._textareaRef.el.value) {
            this.composerView.handleCurrentPartnerIsTyping();
        }
        this._textareaLastInputValue = this._textareaRef.el.value;
        this._updateHeight();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownTextarea(ev) {
        if (!this.composerView) {
            return;
        }
        switch (ev.key) {
            case 'Escape':
                if (this.composerView.hasSuggestions) {
                    ev.preventDefault();
                    this.composerView.closeSuggestions();
                    markEventHandled(ev, 'ComposerTextInput.closeSuggestions');
                }
                break;
            // UP, DOWN, TAB: prevent moving cursor if navigation in mention suggestions
            case 'ArrowUp':
            case 'PageUp':
            case 'ArrowDown':
            case 'PageDown':
            case 'Home':
            case 'End':
            case 'Tab':
                if (this.composerView.hasSuggestions) {
                    // We use preventDefault here to avoid keys native actions but actions are handled in keyUp
                    ev.preventDefault();
                }
                break;
            // ENTER: submit the message only if the dropdown mention proposition is not displayed
            case 'Enter':
                this._onKeydownTextareaEnter(ev);
                break;
        }
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownTextareaEnter(ev) {
        if (!this.composerView) {
            return;
        }
        if (this.composerView.hasSuggestions) {
            ev.preventDefault();
            return;
        }
        if (
            this.props.sendShortcuts.includes('ctrl-enter') &&
            !ev.altKey &&
            ev.ctrlKey &&
            !ev.metaKey &&
            !ev.shiftKey
        ) {
            this.trigger('o-composer-text-input-send-shortcut');
            ev.preventDefault();
            return;
        }
        if (
            this.props.sendShortcuts.includes('enter') &&
            !ev.altKey &&
            !ev.ctrlKey &&
            !ev.metaKey &&
            !ev.shiftKey
        ) {
            this.trigger('o-composer-text-input-send-shortcut');
            ev.preventDefault();
            return;
        }
        if (
            this.props.sendShortcuts.includes('meta-enter') &&
            !ev.altKey &&
            !ev.ctrlKey &&
            ev.metaKey &&
            !ev.shiftKey
        ) {
            this.trigger('o-composer-text-input-send-shortcut');
            ev.preventDefault();
            return;
        }
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
        sendShortcuts: [],
    },
    props: {
        composerViewLocalId: String,
        hasMentionSuggestionsBelowPosition: Boolean,
        isCompact: Boolean,
        /**
         * Keyboard shortcuts from text input to send message.
         */
        sendShortcuts: {
            type: Array,
            element: String,
            validate: prop => {
                for (const shortcut of prop) {
                    if (!['ctrl-enter', 'enter', 'meta-enter'].includes(shortcut)) {
                        return false;
                    }
                }
                return true;
            },
        },
    },
    template: 'mail.ComposerTextInput',
});

registerMessagingComponent(ComposerTextInput, { propsCompareDepth: { sendShortcuts: 1 } });
