/** @odoo-module **/

import { ModelManager } from '@mail/model/model_manager';
import MessagingService from '@mail/services/messaging/messaging';

import env from 'web.commonEnv';
import { serviceRegistry } from 'web.core';

const { EventBus } = owl.core;

async function createMessaging() {
    await new Promise(resolve => {
        /**
         * Called when all JS resources are loaded. This is useful in order
         * to do some processing after other JS files have been parsed, for
         * example new models or patched models that are coming from
         * other modules, because some of those patches might need to be
         * applied before messaging initialization.
         */
        window.addEventListener('load', resolve);
    });
    /**
     * All JS resources are loaded, but not necessarily processed.
     * We assume no messaging-related modules return any Promise,
     * therefore they should be processed *at most* asynchronously at
     * "Promise time".
     */
    await new Promise(resolve => setTimeout(resolve));
    /**
     * Some models require session data, like locale text direction (depends on
     * fully loaded translation).
     */
    await env.session.is_bound;

    env.modelManager.start();
    /**
     * Create the messaging singleton record.
     */
    env.messaging = env.models['mail.messaging'].create();
}

/**
 * Registry of models.
 */
env.models = {};
/**
 * Environment keys used in messaging.
 */
Object.assign(env, {
    autofetchPartnerImStatus: true,
    destroyMessaging() {
        if (env.modelManager) {
            env.modelManager.deleteAll();
            env.messaging = undefined;
        }
    },
    disableAnimation: false,
    isMessagingInitialized() {
        if (!this.messaging) {
            return false;
        }
        return this.messaging.isInitialized;
    },
    /**
     * States whether the environment is in QUnit test or not.
     *
     * Useful to prevent some behaviour in QUnit tests, like applying
     * style of attachment that uses url.
     */
    isQUnitTest: false,
    loadingBaseDelayDuration: 400,
    messaging: undefined,
    messagingBus: new EventBus(),
    /**
     * Promise which becomes resolved when messaging is created.
     *
     * Useful for discuss widget to know when messaging is created, because this
     * is an essential condition to make it work.
     */
    messagingCreatedPromise: createMessaging(),
    modelManager: new ModelManager(env),
});

serviceRegistry.add('messaging', MessagingService);
