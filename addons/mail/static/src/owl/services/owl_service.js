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
            isTest: this.IS_TEST,
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
        if (!this.IS_TEST) {
            window.addEventListener('resize', _.debounce(() => {
                this._resizeGlobalWindow();
            }), 100);
        } else {
            this['test:resize'] = this._resize;
        }
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

    /**
     * Called when browser size changes. Updates the store with new screen sizes
     * and update `isMobile` value accordingly. Useful for components that
     * are dependent on browser size.
     *
     * @private
     * @param {Object} [param0={}] passed data only in test environment
     * @param {integer} [param0.globalWindowInnerHeight]
     * @param {integer} [param0.globalWindowInnerWidth]
     * @param {boolean} [param0.isMobile]
     */
    _resizeGlobalWindow({
        globalWindowInnerHeight,
        globalWindowInnerWidth,
        isMobile,
    }={}) {
        if (this.IS_TEST) {
            // in test environment, use mocked values
            this._store.dispatch('handleGlobalWindowResize', {
                globalWindowInnerHeight: globalWindowInnerHeight ||
                    this._store.state.globalWindow.innerHeight,
                globalWindowInnerWidth: globalWindowInnerWidth ||
                    this._store.state.globalWindow.innerWidth,
                isMobile: isMobile ||
                    this._store.state.isMobile,
            });
        } else {
            this._store.dispatch('handleGlobalWindowResize', {
                globalWindowInnerHeight: window.innerHeight,
                globalWindowInnerWidth: window.innerWidth,
                isMobile: config.device.isMobile,
            });
        }
    },
});

serviceRegistry.add('owl', OwlService);

return OwlService;

});
