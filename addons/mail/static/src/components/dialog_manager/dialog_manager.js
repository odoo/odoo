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
    // Public
    //--------------------------------------------------------------------------

    get dialogManager() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _checkDialogOpen() {
        if (this.dialogManager.dialogs.length > 0) {
            document.body.classList.add('modal-open');
        } else {
            document.body.classList.remove('modal-open');
        }
    }
}

Object.assign(DialogManager, {
    props: { record: Object },
    template: 'mail.DialogManager',
});

registerMessagingComponent(DialogManager);
