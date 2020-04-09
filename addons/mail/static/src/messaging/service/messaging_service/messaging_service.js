odoo.define('mail.messaging.service.Messaging', function (require) {
'use strict';

const { addMessagingToEnv } = require('mail.messaging.messaging_env');

const AbstractService = require('web.AbstractService');
const { serviceRegistry } = require('web.core');
const env = require('web.env');

addMessagingToEnv(env);

const MessagingService = AbstractService.extend({
    env,
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super(...arguments);

        Object.assign(this.env, {
            call: (...args) => this.call(...args),
            do_action: (...args) => this.do_action(...args),
            do_notify: (...args) => this.do_notify(...args),
            do_warn: (...args) => this.do_warn(...args),
            rpc: (...args) => this._rpc(...args),
            trigger_up: (...args) => this.trigger_up(...args),
        });

        /**
         * Messaging initialization.
         */
        const messagingInitializedPromise = this.env.messagingCreatedPromise.then(async () => {
            // TODO FIXME The method uses service specific env keys so it can
            // only be called after a service has properly set up those keys.
            await this.env.messaging.start();
        });
        Object.assign(this.env, {
            messagingInitializedPromise,
        });

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
});

serviceRegistry.add('messaging', MessagingService);

return MessagingService;

});
