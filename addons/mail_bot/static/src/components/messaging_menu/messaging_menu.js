odoo.define('mail_bot/static/src/components/messaging_menu/messaging_menu,js', function (require) {
'use strict';

const components = {
    MessagingMenu: require('mail/static/src/components/messaging_menu/messaging_menu.js'),
};

const { patch } = require('web.utils');

patch(components.MessagingMenu, 'mail_bot/static/src/components/messaging_menu/messaging_menu,js', {

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onOdoobotRequestClicked() {
        const device = this.messagingMenu.messaging.device;
        if (!device.isMobile) {
            this.messagingMenu.close();
        }
    },
});

});
