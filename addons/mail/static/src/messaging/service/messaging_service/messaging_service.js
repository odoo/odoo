odoo.define('mail.messaging.service.Messaging', function (require) {
'use strict';

const {
    checkRelations,
    generateEntities,
} = require('mail.messaging.entity.core');

const AbstractService = require('web.AbstractService');
const { serviceRegistry } = require('web.core');
const env = require('web.env');

const { Store } = owl;
const { EventBus } = owl.core;

const MessagingService = AbstractService.extend({
    env,
    messagingEnvExtension: undefined,
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super(...arguments);

        this._onGlobalLoad = this._onGlobalLoad.bind(this);
        this._listenGlobalWindowLoad();

        /**
         * Environment of the messaging store (messaging env. without store)
         */
        Object.assign(this.env, {
            autofetchPartnerImStatus: true,
            disableAnimation: false,
            call: (...args) => this.call(...args),
            do_action: (...args) => this.do_action(...args),
            do_notify: (...args) => this.do_notify(...args),
            do_warn: (...args) => this.do_warn(...args),
            entities: undefined,
            isMessagingInitialized() {
                if (!this.messaging) {
                    return false;
                }
                return this.messaging.isInitialized;
            },
            messaging: undefined,
            messagingBus: new EventBus(),
            rpc: (...args) => this._rpc(...args),
            trigger_up: (...args) => this.trigger_up(...args),
        }, this.messagingEnvExtension);

        /**
         * Components cannot use web.bus, because they cannot use
         * EventDispatcherMixin, and webclient cannot easily access env.
         * Communication between webclient and components by core.bus
         * (usable by webclient) and messagingBus (usable by components), which
         * the messaging service acts as mediator since it can easily use both
         * kinds of buses.
         */
        this.env.bus.on(
            'hide_home_menu',
            this,
            () => this.env.messagingBus.trigger('hide_home_menu')
        );
        this.env.bus.on(
            'show_home_menu',
            this,
            () => this.env.messagingBus.trigger('show_home_menu')
        );
        this.env.bus.on(
            'will_hide_home_menu',
            this,
            () => this.env.messagingBus.trigger('will_hide_home_menu')
        );
        this.env.bus.on(
            'will_show_home_menu',
            this,
            () => this.env.messagingBus.trigger('will_show_home_menu')
        );

        /**
         * Messaging store
         */
        const store = new Store({
            env: this.env,
            state: {
                entities: {},
                __classEntityObservables: {},
            },
        });

        /**
         * Environment of messaging components (messaging env. with store)
         */
        Object.assign(this.env, { store });
    },
    /**
     * @override
     */
    destroy(...args) {
        this._super(...args);
        this.env.bus.off('hide_home_menu', this);
        this.env.bus.off('show_home_menu', this);
        this.env.bus.off('will_hide_home_menu', this);
        this.env.bus.off('will_show_home_menu', this);
        if (this.env.messaging) {
            this.env.messaging.stop();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Object}
     */
    getEnv() {
        return this.env;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _listenGlobalWindowLoad() {
        window.addEventListener('load', this._onGlobalLoad);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when all JS resources are loaded. This is useful in order to do
     * some processing after other JS have been parsed, e.g. new Entities,
     * patched Entities, etc.
     *
     * @private
     * @returns {Object}
     */
    _onGlobalLoad() {
        let messagingCreatedPromiseResolve;
        let messagingInitializedPromiseResolve;
        const messagingCreatedPromise = new Promise(resolve => {
            messagingCreatedPromiseResolve = resolve;
        });
        const messagingInitializedPromise = new Promise(resolve => {
            messagingInitializedPromiseResolve = resolve;
        });
        this._onGlobalLoad2({
            messagingCreatedPromiseResolve,
            messagingInitializedPromiseResolve,
        });
        return {
            messagingCreatedPromise,
            messagingInitializedPromise,
        };
    },
    /**
     * Continuation of handling global `load` event. This is isolated in another
     * function so that we can make use of `async/await` without making original
     * handler function blocking. This is useful in tests, in order to simulate
     * state of application when messaging has to become initialized or is not
     * yet initialized.
     *
     * @private
     * @param {Object} param0
     * @param {function} param0.messagingCreatedPromiseResolve function which,
     *   when called, notifies that the messaging global entity has been
     *   created, but not necessarily initialized. Useful in tests to start
     *   making assertions at least at this moment. UI has to display something
     *   when messaging has not yet been initialized, usually just a loading
     *   spinner, because this process may take some time.
     * @param {function} param0.messagingInitializedPromiseResolve function
     *   which, when called, notifies that the messaging global entity has been
     *   fully initialized. Useful in most tests that require messaging to
     *   be initialized.
     */
    async _onGlobalLoad2({
        messagingCreatedPromiseResolve,
        messagingInitializedPromiseResolve,
    }) {
        /**
         * All JS resources are loaded, but not necessarily processed. We assume
         * no messaging-related modules do not return any Promise, therefore
         * they should be processed *at most* asynchronously at "Promise time".
         */
        await new Promise(resolve => setTimeout(resolve));

        this.env.entities = generateEntities();
        /**
         * Make environment accessible from Entities. Note that getter is used
         * to prevent recursive data structure.
         */
        for (const Entity of Object.values(this.env.entities)) {
            Object.defineProperty(Entity, 'env', {
                get: () => this.env,
            });
        }
        /**
         * Check that all entity relations are correct, notably one relation
         * should have matching reversed relation.
         */
        checkRelations(this.env.entities);
        for (const Entity of Object.values(this.env.entities)) {
            Entity.init();
        }

        this.env.messaging = this.env.entities.Messaging.create();
        messagingCreatedPromiseResolve();
        await this.env.messaging.start();
        messagingInitializedPromiseResolve();
    },
});

serviceRegistry.add('messaging', MessagingService);

return MessagingService;

});
