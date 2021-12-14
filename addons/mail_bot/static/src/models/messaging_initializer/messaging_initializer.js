/** @odoo-module **/

import { addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging_initializer/messaging_initializer';

addRecordMethods('MessagingInitializer', {
    /**
     * @private
     */
    async _initializeOdooBot() {
        const data = await this.async(() => this.env.services.rpc({
            model: 'mail.channel',
            method: 'init_odoobot',
        }));
        if (!data) {
            return;
        }
        this.env.session.odoobot_initialized = true;
    },
});

patchRecordMethods('MessagingInitializer', {
    /**
     * @override
     */
    async start() {
        await this.async(() => this._super());

        if ('odoobot_initialized' in this.env.session && !this.env.session.odoobot_initialized) {
            this._initializeOdooBot();
        }
    },
});
