/** @odoo-module **/

import { ModelManager } from '@mail/model/model_manager';

import AbstractService from 'web.AbstractService';

export const MessagingService = AbstractService.extend({
    dependencies: ['bus_service'],
    messagingValues: {},
    /**
     * @override
     */
    init(env) {
        this._super(env);
        this.modelManager = new ModelManager(env);
    },
    /**
     * @override
     */
    start() {
        this._super();
        this.modelManager.start(this.messagingValues);
    },
    /**
     * Returns the messaging record once it is initialized. This method should
     * be considered the main entry point to the messaging system for outside
     * code.
     *
     * @returns {mail.messaging}
     **/
    async get() {
        return this.modelManager.getMessaging();
    }
});
