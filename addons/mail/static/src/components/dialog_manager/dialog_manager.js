/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onPatched } = owl;

export class DialogManager extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        onMounted(() => this._mounted());
        onPatched(() => this._patched());
    }

    _mounted() {
        this._checkDialogOpen();
    }

    _patched() {
        this._checkDialogOpen();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _checkDialogOpen() {
        if (!this.messaging || !this.messaging.dialogManager) {
            return;
        }
        if (this.messaging.dialogManager.dialogs.length > 0) {
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
