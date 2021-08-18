/** @odoo-module **/

import { MessagingService } from '@mail/services/messaging/messaging';

import env from 'web.commonEnv';
import { serviceRegistry } from 'web.core';

/**
 * Environment keys used in messaging.
 */
Object.assign(env, {
    isMessagingInitialized() {
        return (
            this.services.messaging.modelManager.messaging &&
            this.services.messaging.modelManager.messaging.isInitialized
        );
    },
});
Object.defineProperty(env, 'messaging', {
    get() {
        return this.services.messaging.modelManager.messaging;
    },
});
Object.defineProperty(env, 'models', {
    get() {
        return this.services.messaging.modelManager.models;
    },
});

serviceRegistry.add('messaging', MessagingService);
