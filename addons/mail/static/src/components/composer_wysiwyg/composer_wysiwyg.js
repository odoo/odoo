odoo.define('mail.composer.wysiwyg', function (require) {
    'use strict';
    const Wysiwyg = require('web_editor.wysiwyg');
    const { markEventHandled } = require('@mail/utils/utils');
    const {
        createRange,
        setSelection,
    } = require('@mail/js/utils');

    const ComposerWysiwyg = Wysiwyg.extend({
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.composer = options.composer;
            this.textInputComponent = options.textInputComponent;
            this._onClickTextarea = this._onClickTextarea.bind(this);
            this._onFocusinTextarea = this._onFocusinTextarea.bind(this);
            this._onFocusoutTextarea = this._onFocusoutTextarea.bind(this);
            this._onKeydownTextarea = this._onKeydownTextarea.bind(this);
            this._onKeyupTextarea = this._onKeyupTextarea.bind(this);
            /**
             * Last content of textarea from input event. Useful to determine
             * whether the current partner is typing something.
             */
            this._textareaLastInputValue = "";
        },

        /**
         *
         * @override
         */
        start: async function () {
            const _super = await this._super.apply(this, arguments);
            this.$editable.on('click', this._onClickTextarea);
            this.$editable.on('focusin', this._onFocusinTextarea);
            this.$editable.on('focusout', this._onFocusoutTextarea);
            this.$editable.on('keydown', this._onKeydownTextarea);
            this.$editable.on('keyup', this._onKeyupTextarea);
            return _super;
        },

        //--------------------------------------------------------------------------
        // Public functions
        //--------------------------------------------------------------------------
        
        /**
         * Cleans the content and the history of the wysiwyg.
         */
        clear: function() {
            this.setValue("<p><br></p>");
            this.odooEditor.historyReset();
        },

        /**
         * Returns whether the given node is self or a children of self.
         * @param {Node} node
         * @returns {boolean}
         */
        contains: function(node) {
            if (!this.toolbar.el || ! this.el) {
                return false;
            }
            return (this.toolbar.el.contains(node) || this.el.contains(node));
        },

        focus: function() {
            this._super();
            this.textInputComponent.saveStateInStore();
        },

        /**
         * Returns the current selection inside the wysiwyg.
         * @returns {Selection}
         */
        getSelection: function() {
            const selection = this.odooEditor.document.getSelection();
            if (this.contains(selection.baseNode)) {
                return selection;
            }
            return this.composer.textInputCursorSelection;
        },

        /**
         * Insert content into composer.textInputCursorSelection position.
         * @param {string} content
         */
        insertIntoTextInput: function(content) {
            this.focus();
            const replaceRange = createRange(
                this.composer.textInputCursorSelection.anchorNode,
                this.composer.textInputCursorSelection.anchorOffset,
                this.composer.textInputCursorSelection.focusNode,
                this.composer.textInputCursorSelection.focusOffset,
            )
            replaceRange.deleteContents();
            const contentNode = document.createTextNode(content);
            replaceRange.insertNode(contentNode);

            /**
             * PLace the current cursor after the inserted content.
             */
            const range = new Range();
            range.setStartAfter(contentNode);
            range.collapse();
            setSelection(range);
            this.textInputComponent.saveStateInStore();
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _onClickTextarea: function() {
            // clicking might change the cursor position
            this.textInputComponent.saveStateInStore();
        },

        /**
         * @private
         */
        _onFocusinTextarea: function() {
            this.composer.focus();
            this.textInputComponent.trigger('o-focusin-composer');
        },

        /**
         * @private
         */
        _onFocusoutTextarea: function(){
            this.textInputComponent.saveStateInStore();
            this.composer.update({ hasFocus: false });
        },


        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onKeydownTextarea: function(ev) {
            switch (ev.key) {
                case 'Escape':
                    if (this.composer.hasSuggestions) {
                        ev.preventDefault();
                        this.composer.closeSuggestions();
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
                    if (this.composer.hasSuggestions) {
                        // We use preventDefault here to avoid keys native actions but actions are handled in keyUp
                        ev.preventDefault();
                    }
                    break;
                // ENTER: submit the message only if the dropdown mention proposition is not displayed
                case 'Enter':
                    this._onKeydownTextareaEnter(ev);
                    break;
            }
        },

        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onKeydownTextareaEnter: function(ev) {
            if (this.composer.hasSuggestions) {
                ev.preventDefault();
                return;
            }
            if (
                this.textInputComponent.props.sendShortcuts.includes('ctrl-enter') &&
                !ev.altKey &&
                ev.ctrlKey &&
                !ev.metaKey &&
                !ev.shiftKey
            ) {
                this.textInputComponent.trigger('o-composer-text-input-send-shortcut');
                ev.preventDefault();
                return;
            }
            if (
                this.textInputComponent.props.sendShortcuts.includes('enter') &&
                !ev.altKey &&
                !ev.ctrlKey &&
                !ev.metaKey &&
                !ev.shiftKey
            ) {
                this.textInputComponent.trigger('o-composer-text-input-send-shortcut');
                ev.preventDefault();
                return;
            }
            if (
                this.textInputComponent.props.sendShortcuts.includes('meta-enter') &&
                !ev.altKey &&
                !ev.ctrlKey &&
                ev.metaKey &&
                !ev.shiftKey
            ) {
                this.textInputComponent.trigger('o-composer-text-input-send-shortcut');
                ev.preventDefault();
                return;
            }
        },

        /**
         * Key events management is performed in a Keyup to avoid intempestive RPC calls
         *
         * @private
         * @param {KeyboardEvent} ev
         */
        _onKeyupTextarea: function(ev) {
            switch (ev.key) {
                case 'Escape':
                    // already handled in _onKeydownTextarea, break to avoid default
                    break;
                // ENTER, HOME, END, UP, DOWN, PAGE UP, PAGE DOWN, TAB: check if navigation in mention suggestions
                case 'Enter':
                    if (this.composer.hasSuggestions) {
                        this.composer.insertSuggestion();
                        this.composer.closeSuggestions();
                        this.textInputComponent.focus();
                    }
                    break;
                case 'ArrowUp':
                case 'PageUp':
                    if (ev.key === 'ArrowUp' && !this.composer.hasSuggestions && !this.composer.textInputContent && this.composer.thread) {
                        this.composer.thread.startEditingLastMessageFromCurrentUser();
                        break;
                    }
                    if (this.composer.hasSuggestions) {
                        this.composer.setPreviousSuggestionActive();
                        this.composer.update({ hasToScrollToActiveSuggestion: true });
                    }
                    break;
                case 'ArrowDown':
                case 'PageDown':
                    if (ev.key === 'ArrowDown' && !this.composer.hasSuggestions && !this.composer.textInputContent && this.composer.thread) {
                        this.composer.thread.startEditingLastMessageFromCurrentUser();
                        break;
                    }
                    if (this.composer.hasSuggestions) {
                        this.composer.setNextSuggestionActive();
                        this.composer.update({ hasToScrollToActiveSuggestion: true });
                    }
                    break;
                case 'Home':
                    if (this.composer.hasSuggestions) {
                        this.composer.setFirstSuggestionActive();
                        this.composer.update({ hasToScrollToActiveSuggestion: true });
                    }
                    break;
                case 'End':
                    if (this.composer.hasSuggestions) {
                        this.composer.setLastSuggestionActive();
                        this.composer.update({ hasToScrollToActiveSuggestion: true });
                    }
                    break;
                case 'Tab':
                    if (this.composer.hasSuggestions) {
                        if (ev.shiftKey) {
                            this.composer.setPreviousSuggestionActive();
                            this.composer.update({ hasToScrollToActiveSuggestion: true });
                        } else {
                            this.composer.setNextSuggestionActive();
                            this.composer.update({ hasToScrollToActiveSuggestion: true });
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
            this.textInputComponent.saveStateInStore();
            if (this._textareaLastInputValue !== this.getValue()) {
                this.composer.handleCurrentPartnerIsTyping();
            }
            this._textareaLastInputValue = this.getValue();
        },
    });

    return ComposerWysiwyg;
});
