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
        this._onAutocompleteSelect = this._onAutocompleteSelect.bind(this);
        this._onAutocompleteSource = this._onAutocompleteSource.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ChatWindow}
     */
    get chatWindow() {
        return this.messaging && this.messaging.models['ChatWindow'].get(this.props.localId);
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when selecting an item in the autocomplete input of the
     * 'new_message' chat window.
     *
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    async _onAutocompleteSelect(ev, ui) {
        const chat = await this.messaging.getChat({ partnerId: ui.item.id });
        if (!chat) {
            return;
        }
        this.messaging.chatWindowManager.openThread(chat, {
            makeActive: true,
            replaceNewMessage: true,
        });
    }

    /**
     * Called when typing in the autocomplete input of the 'new_message' chat
     * window.
     *
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onAutocompleteSource(req, res) {
        this.messaging.models['Partner'].imSearch({
            callback: (partners) => {
                const suggestions = partners.map(partner => {
                    return {
                        id: partner.id,
                        value: partner.nameOrDisplayName,
                        label: partner.nameOrDisplayName,
                    };
                });
                res(_.sortBy(suggestions, 'label'));
            },
            keyword: _.escape(req.term),
            limit: 10,
        });
    }

}

Object.assign(ChatWindow, {
    props: { localId: String },
    template: 'mail.ChatWindow',
});

registerMessagingComponent(ChatWindow);
