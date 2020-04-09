odoo.define('mail_bot.messaging.entity.MessagingInitializer', function (require) {
'use strict';

const { registerClassPatchEntity } = require('mail.messaging.entity.core');

registerClassPatchEntity('MessagingInitializer', 'mail_bot.messaging.entity.MessagingInitializer', {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _showOdoobotTimeout() {
        setTimeout(() => {
            this.env.session.odoobot_initialized = true;
            this.env.rpc({
                model: 'mail.channel',
                method: 'init_odoobot',
            });
        }, 2 * 60 * 1000);
    },
    /**
     * @override
     */
    async _start(messagingInitializer) {
        await this._super(messagingInitializer);

        if ('odoobot_initialized' in this.env.session && !this.env.session.odoobot_initialized) {
            this._showOdoobotTimeout();
        }
    },
});

});
