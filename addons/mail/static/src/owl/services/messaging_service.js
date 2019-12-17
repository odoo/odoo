odoo.define('mail.service.Messaging', function (require) {
'use strict';

const actions = require('mail.store.actions');
const getters = require('mail.store.getters');
const initializeState = require('mail.store.state');

const AbstractService = require('web.AbstractService');
const { serviceRegistry } = require('web.core');
const env = require('web.env');

const { Store } = owl;

const MessagingService = AbstractService.extend({
    /**
     * Optional functions that are called after creating messaging env.
     * Useful to make changes to store in tests.
     */
    registry: {
        initialEnv: env,
        onMessagingEnvCreated: messagingEnv => {},
    },
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super(...arguments);

        const {
            initialEnv,
            onMessagingEnvCreated,
        } = this.registry;

        /**
         * Environment of the messaging store (messaging env. without store)
         */
        let messagingStoreEnv = Object.create(initialEnv);
        Object.assign(messagingStoreEnv, {
            disableAnimation: false,
            call: (...args) => this.call(...args),
            do_action: (...args) => this.do_action(...args),
            do_notify: (...args) => this.do_notify(...args),
            do_warn: (...args) => this.do_warn(...args),
            rpc: (...args) => this._rpc(...args),
            trigger_up: (...args) => this.trigger_up(...args)
        });

        /**
         * Messaging store
         */
        const store = new Store({
            actions,
            env: messagingStoreEnv,
            getters,
            state: initializeState(),
        });

        /**
         * Environment of messaging components (messaging env. with store)
         */
        let messagingEnv = Object.create(messagingStoreEnv);
        Object.assign(messagingEnv, { store });
        onMessagingEnvCreated(messagingEnv);
        store.dispatch('initMessaging');

        this.messagingEnv = messagingEnv;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {Object}
     */
    getMessagingEnv() {
        return this.messagingEnv;
    },
});

serviceRegistry.add('messaging', MessagingService);

return MessagingService;

});
