/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import useUpdate from '@mail/component_hooks/use_update/use_update';
import SuggestionList from '@mail/components/suggestion_list/suggestion_list';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

const { Component } = owl;
const { useRef } = owl.hooks;

const components = { SuggestionList };

class ComposerTextInput extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps({
            compareDepth: {
                sendShortcuts: 1,
            },
        });
        useStore(props => {
            const composer = this.env.models['mail.composer'].get(props.composerLocalId);
            const suggestionList = composer && composer.suggestionList;
            const thread = composer && composer.thread;
            const correspondent = thread ? thread.correspondent : undefined;
            return {
                composerHasFocus: composer && composer.hasFocus,
                composerHasSuggestions: suggestionList && suggestionList.hasSuggestions,
                composerIsLastStateChangeProgrammatic: composer && composer.isLastStateChangeProgrammatic,
                composerIsLog: composer && composer.isLog,
                composerTextInputContent: composer && composer.textInputContent,
                composerTextInputCursorEnd: composer && composer.textInputCursorEnd,
                composerTextInputCursorStart: composer && composer.textInputCursorStart,
                composerTextInputSelectionDirection: composer && composer.textInputSelectionDirection,
                correspondent,
                correspondentNameOrDisplayName: correspondent && correspondent.nameOrDisplayName,
                isDeviceMobile: this.env.messaging.device.isMobile,
                threadDisplayName: thread && thread.displayName,
                threadModel: thread && thread.model,
            };
        });
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
        if (!this.composer.thread) {
            return "";
        }
        if (this.composer.thread.model === 'mail.channel') {
            if (this.composer.thread.correspondent) {
                // TODO SEB (in another PR) missing translation for those
                return _.str.sprintf("Message %s...", this.composer.thread.correspondent.nameOrDisplayName);
            }
            return _.str.sprintf("Message #%s...", this.composer.thread.displayName);
        }
        if (this.composer.isLog) {
            return this.env._t("Log an internal note...");
        }
        return this.env._t("Send a message to followers...");
    }

    focus() {
        this._textareaRef.el.focus();
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
        if (!this.composer) {
            return;
        }
        if (this.composer.isLastStateChangeProgrammatic) {
            this._textareaRef.el.value = this.composer.textInputContent;
            if (this.composer.hasFocus) {
                this._textareaRef.el.setSelectionRange(
                    this.composer.textInputCursorStart,
                    this.composer.textInputCursorEnd,
                    this.composer.textInputSelectionDirection,
                );
            }
            this.composer.update({ isLastStateChangeProgrammatic: false });
        }
        this._updateHeight();
    }

    /**
     * Updates the textarea height.
     *
     * @private
     */
    _updateHeight() {
        this._mirroredTextareaRef.el.value = this.composer.textInputContent;
        this._textareaRef.el.style.height = (this._mirroredTextareaRef.el.scrollHeight) + "px";
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickTextarea() {
        // clicking might change the cursor position
        this.saveStateInStore();
    }

    /**
     * @private
     */
    _onFocusinTextarea() {
        this.composer.focus();
        this.trigger('o-focusin-composer');
    }

    /**
     * @private
     */
    _onFocusoutTextarea() {
        this.saveStateInStore();
        this.composer.update({ hasFocus: false });
    }

    /**
     * @private
     */
    _onInputTextarea() {
        this.saveStateInStore();
        if (this._textareaLastInputValue !== this._textareaRef.el.value) {
            this.composer.handleCurrentPartnerIsTyping();
        }
        this._textareaLastInputValue = this._textareaRef.el.value;
        this._updateHeight();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownTextarea(ev) {
        if (this.composer.suggestionList) {
            this.composer.suggestionList.onKeydown(ev);
        }
        if (
            isEventHandled(ev, 'SuggestionList.suggestionSelected') ||
            isEventHandled(ev, 'SuggestionList.suggestionListClosed') ||
            isEventHandled(ev, 'SuggestionList.navigationUp') ||
            isEventHandled(ev, 'SuggestionList.navigationDown') ||
            isEventHandled(ev, 'SuggestionList.navigationTop') ||
            isEventHandled(ev, 'SuggestionList.navigationBottom')
        ) {
            ev.preventDefault();
            return;
        }
        switch (ev.key) {
            case 'Enter':
                this._onKeydownTextareaEnter(ev);
                break;
            default:
                this.saveStateInStore();
        }
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownTextareaEnter(ev) {
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

}

Object.assign(ComposerTextInput, {
    components,
    defaultProps: {
        hasMentionSuggestionsBelowPosition: false,
        sendShortcuts: [],
    },
    props: {
        composerLocalId: String,
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

export default ComposerTextInput;
