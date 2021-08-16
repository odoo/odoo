/** @odoo-module **/

import MessagingService from '@mail/services/messaging/messaging';
import { makeDeferred } from '@mail/utils/deferred/deferred';

import env from 'web.commonEnv';
import { serviceRegistry } from 'web.core';

/**
 * Environment keys used in messaging.
 */
Object.assign(env, {
    isMessagingInitialized() {
        if (!this.modelManager || !this.modelManager.messaging) {
            return false;
        }
        return this.modelManager.messaging.isInitialized;
    },
    /**
     * Promise which becomes resolved when messaging is created.
     *
     * Useful for discuss widget to know when messaging is created, because this
     * is an essential condition to make it work.
     */
    messagingCreatedPromise: makeDeferred(),
});
Object.defineProperty(env, 'messaging', {
    get() {
        return this.modelManager && this.modelManager.messaging;
    },
});
Object.defineProperty(env, 'models', {
    get() {
        return this.modelManager && this.modelManager.models;
    },
});

serviceRegistry.add('messaging', MessagingService);
