/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';

const { Component } = owl;
const { useRef } = owl.hooks;

class ChatterSearchBox extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        /**
         * Updates the text input content when search box is mounted
         * as input content can't be changed from the DOM.
         */
        useUpdate({ func: () => this._update() });
        /**
         * Reference of the input. Useful to set content.
         */
        this._inputRef = useRef('input');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread|undefined}
     */
    get thread() {
        return this.messaging && this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

    focus() {
        this._inputRef.el.focus();
    }

    /**
     * Saves the text input state in store
     */
    saveStateInStore() {
        this.thread.update({ searchedText: this._inputRef.el.value });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Updates the content
     *
     * @private
     */
    _update() {
        if (!this.thread) {
            return;
        }
        this._inputRef.el.value = this.thread.searchedText;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onFocusout() {
        this.saveStateInStore();
    }
    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        if (ev.key === 'Enter') {
            this.saveStateInStore();
            if (!this._inputRef.el.value) {
                return;
            }
        }
    }

}

Object.assign(ChatterSearchBox, {
    props: {
        threadLocalId: String,
    },
    template: 'mail.ChatterSearchBox',
});

registerMessagingComponent(ChatterSearchBox);
