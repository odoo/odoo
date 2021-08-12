/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { AutocompleteInput } from '@mail/components/autocomplete_input/autocomplete_input';
import { ChatWindowHeader } from '@mail/components/chat_window_header/chat_window_header';
import { ThreadView } from '@mail/components/thread_view/thread_view';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;
const { useRef } = owl.hooks;

const components = { AutocompleteInput, ChatWindowHeader, ThreadView };

export class ChatWindow extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useModels();
        useUpdate({ func: () => this._update() });
        useRefToModel({ fieldName: 'threadRef', modelName: 'mail.chat_window', propNameAsRecordLocalId: 'chatWindowLocalId', refName: 'thread' });
        useComponentToModel({ fieldName: 'component', modelName: 'mail.chat_window', propNameAsRecordLocalId: 'chatWindowLocalId' });
        /**
         * Reference of the autocomplete input (new_message chat window only).
         * Useful when focusing this chat window, which consists of focusing
         * this input.
         */
        this._inputRef = useRef('input');
        /**
         * Reference of thread in the chat window (chat window with thread
         * only). Useful when focusing this chat window, which consists of
         * focusing this thread. Will likely focus the composer of thread, if
         * it has one!
         */
        this._threadRef = useRef('thread');
        this._constructor(...args);
    }

    /**
     * Allows patching constructor.
     */
    _constructor() {}

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.chat_window}
     */
    get chatWindow() {
        return this.env.models['mail.chat_window'].get(this.props.chatWindowLocalId);
    }

    /**
     * Get the content of placeholder for the autocomplete input of
     * 'new_message' chat window.
     *
     * @returns {string}
     */
    get newMessageFormInputPlaceholder() {
        return this.env._t("Search user...");
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Apply visual position of the chat window.
     *
     * @private
     */
    _applyVisibleOffset() {
        const textDirection = this.env.messaging.locale.textDirection;
        const offsetFrom = textDirection === 'rtl' ? 'left' : 'right';
        const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
        this.el.style[offsetFrom] = this.chatWindow.visibleOffset + 'px';
        this.el.style[oppositeFrom] = 'auto';
    }

    /**
     * Focus this chat window.
     *
     * @private
     */
    _focus() {
        this.chatWindow.update({
            isDoFocus: false,
            isFocused: true,
        });
        if (this._inputRef.comp) {
            this._inputRef.comp.focus();
        }
        if (this._threadRef.comp) {
            this._threadRef.comp.focus();
        }
    }

    /**
     * @private
     */
    _update() {
        if (!this.chatWindow) {
            // chat window is being deleted
            return;
        }
        if (this.chatWindow.isDoFocus) {
            this._focus();
        }
        this._applyVisibleOffset();
    }

}

Object.assign(ChatWindow, {
    components,
    defaultProps: {
        hasCloseAsBackButton: false,
        isExpandable: false,
        isFullscreen: false,
    },
    props: {
        chatWindowLocalId: String,
        hasCloseAsBackButton: Boolean,
        isExpandable: Boolean,
        isFullscreen: Boolean,
    },
    template: 'mail.ChatWindow',
});
