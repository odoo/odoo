/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { markEventHandled } from '@mail/utils/utils';
import wysiwygLoader from 'web_editor.loader';
import Widget from 'web.Widget';
import {
    createRange,
    setSelection,
} from '@mail/js/utils';

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
         * Reference of the wysiwygTextarea.
         */
        this._wysiwygTextarea = useRef('wysiwyg_textarea');
        /**
         * Reference of the wysiwyg. Get instance in mounted().
         */
        this._wysiwygRef = undefined;
        this._onClickTextarea = this._onClickTextarea.bind(this);
        this._onFocusinTextarea = this._onFocusinTextarea.bind(this);
        this._onFocusoutTextarea = this._onFocusoutTextarea.bind(this);
        this._onKeydownTextarea = this._onKeydownTextarea.bind(this);
        this._onKeyupTextarea = this._onKeyupTextarea.bind(this);
    }

    mounted() {
        this._createWysiwygIntance();
    }

    willUnmount() {
        if (this._wysiwygRef) {
            this._wysiwygRef.destroy();
        }
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
        if (!this.composerView.composer.activeThread) {
            return "";
        }
        if (this.composerView.composer.activeThread.model === 'mail.channel') {
            if (this.composerView.composer.activeThread.correspondent) {
                return _.str.sprintf(this.env._t("Message %s..."), this.composerView.composer.activeThread.correspondent.nameOrDisplayName);
            }
            return _.str.sprintf(this.env._t("Message #%s..."), this.composerView.composer.activeThread.displayName);
        }
        if (this.composerView.composer.isLog) {
            return this.env._t("Log an internal note...");
        }
        return this.env._t("Send a message to followers...");
    }

    /**
     * Cleans the content and the history of the wysiwyg.
     */
    clear() {
        if (!this._wysiwygRef) {
            return;
        }
        this._wysiwygRef.setValue("<p><br></p>");
        this._wysiwygRef.odooEditor.historyReset();
    }

    /**
     * Returns whether the given node is self or a children of self.
     * @param {Node} node
     * @returns {boolean}
     */
    contains(node) {
        if (!this._wysiwygRef || !this._wysiwygRef.toolbar.el || ! this._wysiwygRef.el) {
            return false;
        }
        return (this._wysiwygRef.toolbar.el.contains(node) || this._wysiwygRef.el.contains(node));
    }

    focus() {
        if (!this._wysiwygRef) {
            return;
        }
        this._wysiwygRef.focus();
        this.saveStateInStore();
    }

    /**
     * Provide the getter for composer_view model,
     * should be refactored when odoo wysiwyg is implmented with OWL.
     */
    getContent() {
        return this._getContent();
    }

    /**
     * Saves the composer text input state in store
     */
    saveStateInStore() {
        this.composerView.composer.update({
            textInputContent: this._getContent(),
            textInputCursorSelection: this._getSelection(),
        });
    }

    /**
     * Insert the content into the wysiwyg.
     */
    insertIntoTextInput(content) {
        if (!this._wysiwygRef) {
            return;
        }
        /**
         * PLace the current cursor after the inserted content.
         */
        const range = new Range();
        const contentNode = document.createTextNode(content);
        // Replacing the content of the editor while it is empty, preventing unwanted </br>
        if(this._wysiwygRef.el.innerHTML.trim() === "" || this._wysiwygRef.el.innerText.trim() === ""){
            this._wysiwygRef.el.lastChild.removeChild(this._wysiwygRef.el.lastChild.lastChild);
            this._wysiwygRef.el.lastChild.append(contentNode);
        } else {
            const replaceRange = createRange(
                this.composerView.composer.textInputCursorSelection.anchorNode,
                this.composerView.composer.textInputCursorSelection.anchorOffset,
                this.composerView.composer.textInputCursorSelection.focusNode,
                this.composerView.composer.textInputCursorSelection.focusOffset,
            )
            replaceRange.deleteContents();
            replaceRange.insertNode(contentNode);
        }
        range.setStartAfter(contentNode);
        range.collapse();
        setSelection(range);
        this.saveStateInStore();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Create the wysiwyg instance.
     *
     * @private
     * @returns {Promise}
     */
     async _createWysiwygIntance () {
        const options = {
            disableCommandBar: true,
            disableTab: true,
            placeholder: this.textareaPlaceholder,
            resizable: false,
            toolbarTemplate: 'mail.composer_toolbar',
            userGeneratedContent: true,
        };
        await wysiwygLoader.loadFromTextarea(new Widget(), this._wysiwygTextarea.el, options).then((wys) => {
            this._wysiwygRef = wys;
            this._wysiwygRef.$el.addClass('o_ComposerTextInput_wysiwyg');
            this._wysiwygRef.el.addEventListener('click', this._onClickTextarea);
            this._wysiwygRef.el.addEventListener('focusin', this._onFocusinTextarea);
            this._wysiwygRef.el.addEventListener('focusout', this._onFocusoutTextarea);
            this._wysiwygRef.el.addEventListener('keydown', this._onKeydownTextarea);
            this._wysiwygRef.el.addEventListener('keyup', this._onKeyupTextarea);
            if (!this.composerView) {
                return;
            }
            /**
             * Updates the state of the wysiwyg widget when ready.
             * Do manully stateChange/focus when wysiwyg is ready,
             * aiming to prevent unexpected behaviours happen.
             */
             this.render();
        });
    }

    /**
     * Returns textarea current content.
     *
     * @private
     * @returns {string}
     */
    _getContent() {
        if(!this._wysiwygRef || this._wysiwygRef.el.innerText.trim() === "") {
            return "";
        }
        return this._wysiwygRef.getValue();
    }

    /**
     * Returns selection.
     *
     * @private
     * @returns {Selection}
     */
    _getSelection() {
        if (!this._wysiwygRef) {
            return "";
        }
        let selection = this._wysiwygRef.odooEditor.document.getSelection();
        if (this.contains(selection.baseNode)) {
            return {
                anchorNode: selection.anchorNode,
                anchorOffset: selection.anchorOffset,
                focusNode: selection.focusNode,
                focusOffset: selection.focusOffset,
                isCollapsed: selection.isCollapsed,
            };
        }
        return this.composerView.composer.textInputCursorSelection;
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
     * Updates the content
     *
     * @private
     */
    _update() {
        if (!this.composerView) {
            return;
        }
        if(!this._wysiwygRef) {
            return ;
        }
        const parser = new DOMParser();
        const htmlDoc = parser.parseFromString(this.composerView.composer.textInputContent, 'text/html');
        if (this.composerView.composer.isLastStateChangeProgrammatic) {
            this.composerView.composer.update({ isLastStateChangeProgrammatic: false });
            if (htmlDoc.body.textContent == '') {
                this._wysiwygRef.el.innerHTML = '<p></br></p>';
                return ;
            }
            this._wysiwygRef.el.innerHTML = this.composerView.composer.textInputContent;
            if (this.composerView.hasFocus && this.composerView.composer.textInputCursorSelection) {
                const range = createRange(
                    this.composerView.composer.textInputCursorSelection.anchorNode,
                    this.composerView.composer.textInputCursorSelection.anchorOffset,
                    this.composerView.composer.textInputCursorSelection.focusNode,
                    this.composerView.composer.textInputCursorSelection.focusOffset,
                )
                setSelection(range);
            }
        }
        if (this.composerView.doFocus) {
            this.composerView.update({ doFocus: false });
            if (this.messaging.device.isMobile) {
                this.el.scrollIntoView();
            }
            this._wysiwygRef.focus();
        }
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
                break;
        }
        this.saveStateInStore();
        if (this._textareaLastInputValue !== this._wysiwygRef.getValue()) {
            this.composerView.handleCurrentPartnerIsTyping();
        }
        this._textareaLastInputValue = this._wysiwygRef.getValue();
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
