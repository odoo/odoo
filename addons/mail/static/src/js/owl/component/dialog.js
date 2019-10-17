odoo.define('mail.component.Dialog', function (require) {
'use strict';

class Dialog extends owl.Component {
    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this._componentRef = owl.hooks.useRef('component');
        this._globalClickEventListener = ev => this._onClickGlobal(ev);
    }

    mounted() {
        document.addEventListener('click', this._globalClickEventListener);
    }

    willUnmount() {
        document.removeEventListener('click', this._globalClickEventListener);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        ev.stopPropagation();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickGlobal(ev) {
        if (ev.target.closest(`.o_Dialog_component[data-dialog-id="${this.props.id}"]`)) {
            return;
        }
        if (!this._componentRef.comp.isCloseable()) {
            return;
        }
        this.trigger('o-close', {
            id: this.props.id,
        });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onClose(ev) {
        this.trigger('o-close', {
            id: this.props.id,
        });
    }
}

Dialog.props = {
    Component: Object,
    id: String,
    info: Object,
};

Dialog.template = 'mail.component.Dialog';

return Dialog;

});
