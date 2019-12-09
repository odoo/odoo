odoo.define('mail.service.Owl', function (require) {
'use strict';

const AbstractService = require('web.AbstractService');
const config = require('web.config');
const { _t, qwebOwl, serviceRegistry } = require('web.core');
const session = require('web.session');

const actions = require('mail.store.actions');
const getters = require('mail.store.getters');
const { init: initState } = require('mail.store.state');

const { Store } = owl;

const OwlService = AbstractService.extend({
    IS_DEV: true,
    IS_TEST: false,
    TEST_STORE_INIT_STATE: {},
    dependencies: ['ajax', 'bus_service', 'local_storage'],
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        if (this.IS_DEV) {
            window.owl_service = this;
        }
        this._env = undefined;
        this._store = undefined;
    },
    /**
     * @override
     */
    start() {
        this._super(...arguments);
        this._env = {
            _t,
            disableAnimation: this.IS_TEST,
            qweb: qwebOwl,
            session,
            call: (...args) => this.call(...args),
            do_action: (...args) => this.do_action(...args),
            do_notify: (...args) => this.do_notify(...args),
            do_warn: (...args) => this.do_warn(...args),
            rpc: (...args) => this._rpc(...args),
            trigger_up: (...args) => this.trigger_up(...args),
        };

        let state = initState(this.IS_TEST ? this.TEST_STORE_INIT_STATE : undefined);
        if (this.IS_TEST) {
            actions._startLoopFetchPartnerImStatus = () => {};
            actions._loopFetchPartnerImStatus = () => {};
        }
        this._store = new Store({ actions, env: this._env, getters, state });
        if (this.IS_DEV) {
            window.store = this.store;
        }

        this._store.dispatch('initMessaging');
        window.addEventListener('resize', _.debounce(() => {
            this._resizeGlobalWindow();
        }), 100);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {Object}
     */
    getEnv() {
        return Object.assign({ store: this._store }, this._env);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _resizeGlobalWindow() {
        this._store.dispatch('handleGlobalWindowResize', {
            globalWindowInnerHeight: window.innerHeight,
            globalWindowInnerWidth: window.innerWidth,
            isMobile: config.device.isMobile,
        });
    },
});

serviceRegistry.add('owl', OwlService);

return OwlService;

});
