odoo.define('mail.component.Dialog', function (require) {
'use strict';

const { Component } = owl;
const { useRef } = owl.hooks;

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
    }

    mounted() {
        document.addEventListener('click', this._onClickGlobal, true);
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickGlobal, true);
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
        this.trigger('o-close', { id: this.props.id });
    }

    /**
     * Called when component of this dialog asks to close this dialog.
     *
     * @private
     * @param {CustomEvent} ev
     */
    _onClose(ev) {
        this.trigger('o-close', { id: this.props.id });
    }
}

Dialog.props = {
    componentName: String,
    id: String,
    info: Object,
};

Dialog.template = 'mail.component.Dialog';

return Dialog;

});
