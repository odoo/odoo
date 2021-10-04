/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import wysiwygLoader from '@mail/js/frontend/loader';
import Widget from 'web.Widget';

const { Component } = owl;
const { useRef } = owl.hooks;

/**
 * This component is used as middleware to connect OWL and legacy widget.
 * Theoretically, composer and wysiwyg should have a one2one relationship according the OWL framework.
 */
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
         * Reference of the wysiwyg. Get instance when in mounted() lifecycle.
         */
        this._wysiwygRef = undefined;

        this._createWysiwygIntance = this._createWysiwygIntance.bind(this);
        this._getContent = this._getContent.bind(this);
        this._getSelection = this._getSelection.bind(this);
    }

    mounted() {
        this._createWysiwygIntance();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.composer}
     */
    get composer() {
        return this.messaging && this.messaging.models['mail.composer'].get(this.props.composerLocalId);
    }

    /**
     * @returns {string}
     */
    get textareaPlaceholder() {
        if (!this.composer) {
            return "";
        }
        if (!this.composer.activeThread) {
            return "";
        }
        if (this.composer.activeThread.model === 'mail.channel') {
            if (this.composer.activeThread.correspondent) {
                return _.str.sprintf("Message %s...", this.composer.activeThread.correspondent.nameOrDisplayName);
            }
            return _.str.sprintf("Message #%s...", this.composer.activeThread.displayName);
        }
        if (this.composer.isLog) {
            return this.env._t("Log an internal note...");
        }
        return this.env._t("Send a message to followers...");
    }

    focus() {
        if (this._wysiwygRef) {
            this._wysiwygRef.focus();
        }
    }

    focusout() {
        this.saveStateInStore();
        this._wysiwygRef.el.blur();
    }

    /**
     * Saves the composer text input state in store
     */
    saveStateInStore() {
        this.composer.update({
            textInputContent: this._getContent(),
            textInputCursorSelection: this._getSelection(),
        });
    }

    /**
     * Insert the content into the wysiwyg.
     */
    insertIntoTextInput(content) {
        this._wysiwygRef.insertIntoTextInput(content);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Create the wysiwyg instance
     *
     * @private
     * @returns {Promise}
     */
     async _createWysiwygIntance () {
        var options = {
            composer: this.composer,
            disableCommandBar: true,
            placeholder: this.textareaPlaceholder,
            resizable: false,
            textInputComponent: this,
            toolbarTemplate: 'mail.composer_toolbar',
            userGeneratedContent: true,
        };
        this._wysiwygRef = await wysiwygLoader.loadFromTextarea(new Widget(), this._textareaRef.el, options);
        /**
         * Updates the initial state of the wysiwyg widget when ready.
         * Calling this.focus() when wysiwyg ref is not fully prepared cause unexpected error.
         * Checking the state of composer and do manully focus after wysiwyg is ready is to
         * prevent the unexpected behaviour happens.
         */
        if (this.composer.isLastStateChangeProgrammatic) {
            this._wysiwygRef.el.innerHTML = this.composer.textInputContent;
            this.composer.update({ isLastStateChangeProgrammatic: false });
        }
        if (this.composer.doFocus) {
            this.focus();
            this.composer.update({ doFocus: false });
        }
    }
    /**
     * Returns current content.
     *
     * @private
     * @returns {string}
     */
    _getContent() {
        if(this._wysiwygRef.el.innerText.trim() === "") {
            return "";
        }
        return this._wysiwygRef.getValue();
    }

    /**
     * Returns current selection.
     *
     * @private
     * @returns {Selection}
     */
    _getSelection() {
        return this._wysiwygRef.getSelection();
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
        if (this.composer.doFocus && this._wysiwygRef) {
            this.focus();
            this.composer.update({ doFocus: false });
        }
        if (this.composer.isLastStateChangeProgrammatic && this._wysiwygRef) {
            this._wysiwygRef.el.innerHTML = this.composer.textInputContent;
            this.composer.update({ isLastStateChangeProgrammatic: false });
        }
    }

}

Object.assign(ComposerTextInput, {
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

registerMessagingComponent(ComposerTextInput, { propsCompareDepth: { sendShortcuts: 1 } });
