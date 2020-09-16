odoo.define('mail/static/src/js/main.js', function (require) {
'use strict';

const ModelManager = require('mail/static/src/model/model_manager.js');

const env = require('web.commonEnv');

const { Store } = owl;
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
 * Messaging store
 */
const store = new Store({
    env,
    state: {
        messagingRevNumber: 0,
    },
});

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
    store,
});

/**
 * Components cannot use web.bus, because they cannot use
 * EventDispatcherMixin, and webclient cannot easily access env.
 * Communication between webclient and components by core.bus
 * (usable by webclient) and messagingBus (usable by components), which
 * the messaging service acts as mediator since it can easily use both
 * kinds of buses.
 */
env.bus.on(
    'hide_home_menu',
    null,
    () => env.messagingBus.trigger('hide_home_menu')
);
env.bus.on(
    'show_home_menu',
    null,
    () => env.messagingBus.trigger('show_home_menu')
);
env.bus.on(
    'will_hide_home_menu',
    null,
    () => env.messagingBus.trigger('will_hide_home_menu')
);
env.bus.on(
    'will_show_home_menu',
    null,
    () => env.messagingBus.trigger('will_show_home_menu')
);

env.messagingCreatedPromise.then(() => env.messaging.start());

});
