odoo.define('mail.component.DialogManager', function (require) {
"use strict";

const Dialog = require('mail.component.Dialog');

class DialogManager extends owl.store.ConnectedComponent {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.DEBUG = true;
        if (this.DEBUG) {
            window.dialog_manager = this;
        }
    }

    mounted() {
        this._checkDialogOpen();
    }

    patched() {
        this._checkDialogOpen();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _checkDialogOpen() {
        if (this.storeProps.dialogs.length > 0) {
            document.body.classList.add('modal-open');
        } else {
            document.body.classList.remove('modal-open');
        }
    }
}

DialogManager.components = {
    Dialog,
};

/**
 * @param {Object} state
 * @return {Object}
 */
DialogManager.mapStoreToProps = function (state) {
    return {
        ...state.dialogManager,
    };
};

DialogManager.template = 'mail.component.DialogManager';

return DialogManager;

});
