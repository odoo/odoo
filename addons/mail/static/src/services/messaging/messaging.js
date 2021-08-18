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
});
