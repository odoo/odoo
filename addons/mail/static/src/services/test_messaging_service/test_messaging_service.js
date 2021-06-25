/** @odoo-module **/

import { ModelManager } from '@mail/model/model_manager';

import { registry } from '@web/core/registry';

const { Store } = owl;
const { EventBus } = owl.core;

class TestMessagingService {

    constructor(env) {
        this.env = env;
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
        this.models = {};
        /**
         * Environment keys used in messaging.
         */
        Object.assign(this, {
            autofetchPartnerImStatus: true,
            destroyMessaging() {
                if (this.modelManager) {
                    this.modelManager.deleteAll();
                    this.messaging = undefined;
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
            messagingCreatedPromise: this.createMessaging(),
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
            () => this.messagingBus.trigger('hide_home_menu')
        );
        env.bus.on(
            'show_home_menu',
            null,
            () => this.messagingBus.trigger('show_home_menu')
        );
        env.bus.on(
            'will_hide_home_menu',
            null,
            () => this.messagingBus.trigger('will_hide_home_menu')
        );
        env.bus.on(
            'will_show_home_menu',
            null,
            () => this.messagingBus.trigger('will_show_home_menu')
        );

    }

    async createMessaging() {
        this.modelManager.start();
        /**
         * Create the messaging singleton record.
         */
        this.messaging = this.models['mail.messaging'].create();
    }

    start() {
        this.messagingCreatedPromise.then(
            () => {
                this.messaging.start();
            },
        );
    }
}

export const testMessagingService = {
    dependencies: ['localization', 'orm'],
    start(env) {
        const messagingService = new TestMessagingService(env);
        messagingService.start();
        return messagingService;
    },
};

registry.category('services').add('messaging', testMessagingService);
