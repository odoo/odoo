odoo.define('mail.messaging.component.DialogManager', function (require) {
'use strict';

const components = {
    Dialog: require('mail.messaging.component.Dialog'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class DialogManager extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                Dialog: this.env.entities.Dialog.observable,
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
        if (this.env.entities.Dialog.all.length > 0) {
            document.body.classList.add('modal-open');
        } else {
            document.body.classList.remove('modal-open');
        }
    }

}

Object.assign(DialogManager, {
    components,
    props: {},
    template: 'mail.messaging.component.DialogManager',
});

return DialogManager;

});
