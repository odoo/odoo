odoo.define('mail_bot.messaging.component.MessagingMenu', function (require) {
'use strict';

const components = {
    MessagingMenu: require('mail.messaging.component.MessagingMenu'),
};

const { patch } = require('web.utils');

patch(components.MessagingMenu, 'mail_bot.messaging.component.MessagingMenu', {

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onOdoobotRequestClicked() {
        const device = this.env.messaging.device;
        if (!device.isMobile) {
            this.messagingMenu.close();
        }
    },
});

});
