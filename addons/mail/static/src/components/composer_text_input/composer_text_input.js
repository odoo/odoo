odoo.define('mail/static/src/components/composer_text_input/composer_text_input.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const components = {
    PartnerMentionSuggestion: require('mail/static/src/components/partner_mention_suggestion/partner_mention_suggestion.js'),
};
const { markEventHandled } = require('mail/static/src/utils/utils.js');

const { Component } = owl;
const { useRef } = owl.hooks;

/**
 * ComposerInput relies on a minimal HTML editor in order to support mentions.
 */
class ComposerTextInput extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const composer = this.env.models['mail.composer'].get(props.composerLocalId);
            return {
                composer: composer ? composer.__state : undefined,
                isDeviceMobile: this.env.messaging.device.isMobile,
            };
        });
        /**
         * Last content of textarea from input event. Useful to determine
         * whether the current partner is typing something.
         */
        this._textareaLastInputValue = "";
        /**
         * Reference of the textarea. Useful to set height, selection and content.
         */
        this._textareaRef = useRef('textarea');
    }

    /**
     * Updates the composer text input content when composer is mounted
     * as textarea content can't be changed from the DOM.
     */
    mounted() {
        this._update();
    }

    /**
     * Updates the composer text input content when composer has changed
     * as textarea content can't be changed from the DOM.
     */
    patched() {
        this._update();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.composer}
     */
    get composer() {
        return this.env.models['mail.composer'].get(this.props.composerLocalId);
    }

    /**
     * @returns {string}
     */
    get textareaPlaceholder() {
        if (!this.composer) {
            return "";
        }
        if (this.composer.thread && this.composer.thread.model !== 'mail.channel') {
            if (this.composer.isLog) {
                return this.env._t("Log an internal note...");
            }
            return this.env._t("Send a message to followers...");
        }
        return this.env._t("Write something...");
    }

    focusout() {
        this.saveStateInStore();
        this._textareaRef.el.blur();
    }

    /**
     * Saves the composer text input state in store
     */
    saveStateInStore() {
        this.composer.update({
            textInputContent: this._getContent(),
            textInputCursorStart: this._getSelectionStart(),
            textInputCursorEnd: this._getSelectionEnd(),
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
        this._textareaRef.el.value = this.composer.textInputContent;
        this._textareaRef.el.setSelectionRange(
            this.composer.textInputCursorStart,
            this.composer.textInputCursorEnd
        );
        this._updateHeight();
        if (this.composer.isDoFocus) {
            this._textareaRef.el.focus();
            this.composer.update({ isDoFocus: false });
        }
    }

    /**
     * Updates the textarea height.
     *
     * @private
     */
    _updateHeight() {
        this._textareaRef.el.style.height = "0px";
        this._textareaRef.el.style.height = (this._textareaRef.el.scrollHeight) + "px";
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onFocusinTextarea() {
        this.composer.update({ hasFocus: true });
    }

    /**
     * @private
     */
    _onFocusoutTextarea() {
        this.composer.update({ hasFocus: false });
    }

    /**
     * @private
     */
    _onInputTextarea() {
        if (this._textareaLastInputValue !== this._textareaRef.el.value) {
            this.composer.handleCurrentPartnerIsTyping();
        }
        this._textareaLastInputValue = this._textareaRef.el.value;
        this._updateHeight();
        this.saveStateInStore();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownTextarea(ev) {
        switch (ev.key) {
            case 'Escape':
                if (this.composer.hasSuggestedPartners) {
                    ev.preventDefault();
                    this.composer.closeMentionSuggestions();
                    markEventHandled(ev, 'ComposerTextInput.closeMentionSuggestions');
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
                if (this.composer.hasSuggestedPartners) {
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
        if (this.composer.hasSuggestedPartners) {
            ev.preventDefault();
        } else {
            if (!this.props.hasSendOnEnterEnabled) {
                return;
            }
            if (ev.shiftKey) {
                return;
            }
            if (this.env.messaging.device.isMobile) {
                return;
            }
            this.trigger('o-keydown-enter');
            ev.preventDefault();
        }
    }

    /**
     * Key events management is performed in a Keyup to avoid intempestive RPC calls
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeyupTextarea(ev) {
        switch (ev.key) {
            case 'Escape':
                // already handled in _onKeydownTextarea, break to avoid default
                break;
            // ENTER, HOME, END, UP, DOWN, PAGE UP, PAGE DOWN, TAB: check if navigation in mention suggestions
            case 'Enter':
                if (this.composer.hasSuggestedPartners) {
                    if (this.composer.activeSuggestedPartner) {
                        this.composer.insertMentionedPartner(this.composer.activeSuggestedPartner);
                        this.composer.closeMentionSuggestions();
                        this.composer.focus();
                    }
                }
                break;
            case 'ArrowUp':
            case 'PageUp':
                if (this.composer.hasSuggestedPartners) {
                    this.composer.setPreviousSuggestedPartnerActive();
                }
                break;
            case 'ArrowDown':
            case 'PageDown':
                if (this.composer.hasSuggestedPartners) {
                    this.composer.setNextSuggestedPartnerActive();
                }
                break;
            case 'Home':
                if (this.composer.hasSuggestedPartners) {
                    this.composer.setFirstSuggestedPartnerActive();
                }
                break;
            case 'End':
                if (this.composer.hasSuggestedPartners) {
                    this.composer.setLastSuggestedPartnerActive();
                }
                break;
            case 'Tab':
                if (this.composer.hasSuggestedPartners) {
                    if (ev.shiftKey) {
                        this.composer.setPreviousSuggestedPartnerActive();
                    } else {
                        this.composer.setNextSuggestedPartnerActive();
                    }
                }
                break;
            // Otherwise, check if a mention is typed
            default:
                this.saveStateInStore();
                this.composer._detectDelimiter();
        }
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onPartnerMentionSuggestionClicked(ev) {
        this.composer.insertMentionedPartner(ev.detail.partner);
        this.composer.closeMentionSuggestions();
        this.composer.focus();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPartnerMentionSuggestionMouseOver(ev) {
        this.composer.update({
            activeSuggestedPartner: [['link', ev.detail.partner]],
        });
    }

}

Object.assign(ComposerTextInput, {
    components,
    defaultProps: {
        hasMentionSuggestionsBelowPosition: false,
        hasSendOnEnterEnabled: true,
    },
    props: {
        hasMentionSuggestionsBelowPosition: Boolean,
        hasSendOnEnterEnabled: Boolean,
        composerLocalId: String,
    },
    template: 'mail.ComposerTextInput',
});

return ComposerTextInput;

});
