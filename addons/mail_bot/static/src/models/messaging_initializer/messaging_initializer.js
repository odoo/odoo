odoo.define('mail_bot/static/src/models/messaging_initializer/messaging_initializer.js', function (require) {
'use strict';

const { registerInstancePatchModel } = require('mail/static/src/model/model_core.js');

registerInstancePatchModel('mail.messaging_initializer', 'mail_bot/static/src/models/messaging_initializer/messaging_initializer.js', {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _showOdoobotTimeout() {
        setTimeout(() => {
            this.env.session.odoobot_initialized = true;
            this.env.services.rpc({
                model: 'mail.channel',
                method: 'init_odoobot',
            });
        }, 2 * 60 * 1000);
    },
    /**
     * @override
     */
    async _start() {
        await this.async(() => this._super());

        if ('odoobot_initialized' in this.env.session && !this.env.session.odoobot_initialized) {
            this._showOdoobotTimeout();
        }
    },
});

});
