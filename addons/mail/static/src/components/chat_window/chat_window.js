/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChatWindow extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdate({ func: () => this._update() });
        /**
         * Reference of the autocomplete input (new_message chat window only).
         * Useful when focusing this chat window, which consists of focusing
         * this input.
         */
        this._inputRef = { el: null };
        // the following are passed as props to children
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ChatWindow}
     */
    get chatWindow() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (!this.chatWindow) {
            // chat window is being deleted
            return;
        }
        if (!this.root.el) {
            return;
        }
        if (this.chatWindow.isDoFocus) {
            this.chatWindow.update({ isDoFocus: false });
            if (this._inputRef.el) {
                this._inputRef.el.focus();
            }
        }
    }

}

Object.assign(ChatWindow, {
    props: { record: Object },
    template: 'mail.ChatWindow',
});

registerMessagingComponent(ChatWindow);
