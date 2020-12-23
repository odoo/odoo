odoo.define('mail/static/src/components/dialog_manager/dialog_manager.js', function (require) {
'use strict';

const components = {
    Dialog: require('mail/static/src/components/dialog/dialog.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class DialogManager extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const dialogManager = this.env.messaging && this.env.messaging.dialogManager;
            return {
                dialogManager: dialogManager ? dialogManager.__state : undefined,
            };
        });
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
        if (!this.env.messaging) {
            /**
             * Messaging not created, which means essential models like
             * dialog manager are not ready, so open status of dialog in DOM
             * is omitted during this (short) period of time.
             */
            return;
        }
        if (this.env.messaging.dialogManager.dialogs.length > 0) {
            document.body.classList.add('modal-open');
        } else {
            document.body.classList.remove('modal-open');
        }
    }

}

Object.assign(DialogManager, {
    components,
    props: {},
    template: 'mail.DialogManager',
});

return DialogManager;

});
