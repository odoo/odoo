/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onWillUnmount } = owl;

export class Dialog extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this._onClickGlobal = this._onClickGlobal.bind(this);
        this._onKeydownDocument = this._onKeydownDocument.bind(this);
        onMounted(() => this._mounted());
        onWillUnmount(() => this._willUnmount());
    }

    _mounted() {
        document.addEventListener('click', this._onClickGlobal, true);
        document.addEventListener('keydown', this._onKeydownDocument);
    }

    _willUnmount() {
        document.removeEventListener('click', this._onClickGlobal, true);
        document.removeEventListener('keydown', this._onKeydownDocument);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Dialog}
     */
    get dialog() {
        return this.messaging && this.messaging.models['Dialog'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on this dialog.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        ev.stopPropagation();
    }

    /**
     * Closes the dialog when clicking outside.
     * Does not work with attachment viewer because it takes the whole space.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickGlobal(ev) {
        if (this.dialog.hasElementInContent(ev.target)) {
            return;
        }
        if (!this.dialog.isCloseable) {
            return;
        }
        this.dialog.delete();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownDocument(ev) {
        if (ev.key === 'Escape') {
            this.dialog.delete();
        }
    }

}

Object.assign(Dialog, {
    props: { localId: String },
    template: 'mail.Dialog',
});

registerMessagingComponent(Dialog);
