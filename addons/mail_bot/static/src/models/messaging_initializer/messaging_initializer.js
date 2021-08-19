/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';

registerInstancePatchModel('mail.messaging_initializer', 'mail_bot/static/src/models/messaging_initializer/messaging_initializer.js', {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _initializeOdooBot() {
        const data = await this.messaging.rpcOrmStatic('mail.channel', 'init_odoobot');
        if (!data || !this.exists()) {
            return;
        }
        this.env.session.odoobot_initialized = true;
    },

    /**
     * @override
     */
    async start() {
        await this._super();
        if (!this.exists()) {
            return;
        }
        if ('odoobot_initialized' in this.env.session && !this.env.session.odoobot_initialized) {
            this._initializeOdooBot();
        }
    },
});
