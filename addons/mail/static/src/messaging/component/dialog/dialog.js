odoo.define('mail.messaging.component.Dialog', function (require) {
'use strict';

const { Component } = owl;
const { useRef, useStore } = owl.hooks;

class Dialog extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        /**
         * Reference to the component used inside this dialog.
         */
        this._componentRef = useRef('component');
        this._onClickGlobal = this._onClickGlobal.bind(this);
        useStore(props => {
            return {
                dialog: this.env.entities.Dialog.get(props.dialogLocalId),
            };
        });
    }

    mounted() {
        document.addEventListener('click', this._onClickGlobal, true);
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Dialog}
     */
    get dialog() {
        return this.env.entities.Dialog.get(this.props.dialogLocalId);
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
        if (this.el.contains(ev.target)) {
            return;
        }
        // TODO SEB this should be child logic (will crash if child doesn't have isCloseable!!)
        if (!this._componentRef.comp.isCloseable()) {
            return;
        }
        this.dialog.close();
    }

}

Object.assign(Dialog, {
    props: {
        dialogLocalId: String,
    },
    template: 'mail.messaging.component.Dialog',
});

return Dialog;

});
