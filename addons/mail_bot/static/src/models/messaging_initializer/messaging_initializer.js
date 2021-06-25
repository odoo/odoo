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
        const data = await this.async(() => this.env.services.orm.call(
            'mail.channel',
            'init_odoobot',
        ));
        if (!data) {
            return;
        }
        this.messaging.update({ odoobot_initialized: true });
    },

    /**
     * @override
     */
    _init(data) {
        this._super(data);
        this.messaging.update({ odoobot_initialized: data.odoobot_initialized });
        if (!this.messaging.odoobot_initialized) {
            this._initializeOdooBot();
        }
    },
});
