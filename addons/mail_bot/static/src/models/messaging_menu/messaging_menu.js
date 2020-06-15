odoo.define('mail_bot/static/src/models/messaging_menu/messaging_menu.js', function (require) {
'use strict';

const { registerInstancePatchModel } = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.messaging_menu', 'mail_bot/static/src/models/messaging_menu/messaging_menu.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _updateCounter() {
        let counter = this._super();
        if (!this.messaging) {
            // compute after delete
            return counter;
        }
        if (this.messaging.isNotificationPermissionDefault()) {
            counter += 1;
        }
        return counter;
    },
});

});
