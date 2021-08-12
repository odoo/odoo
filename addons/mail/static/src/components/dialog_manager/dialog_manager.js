/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DialogManager extends Component {

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
    props: {},
    template: 'mail.DialogManager',
});

registerMessagingComponent(DialogManager);
