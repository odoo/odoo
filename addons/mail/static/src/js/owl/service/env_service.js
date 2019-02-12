odoo.define('mail.service.Env', function (require) {
"use strict";

const AbstractService = require('web.AbstractService');
const core = require('web.core');
const session = require('web.session');

const DEBUG = true;
const _t = core._t;

const EnvService = AbstractService.extend({
    TEST_ENV: {
        active: false,
    },
    /**
     * @override {web.AbstractService}
     */
    init() {
        this._super.apply(this, arguments);
        if (DEBUG) {
            window.env_service = this;
        }
    },
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super.apply(this, arguments);
        this.env = {
            _t,
            isTestEnv: this.TEST_ENV.active,
            qweb: core.qwebOwl,
            session,
            call: (...args) => this.call(...args),
            do_action: (...args) => this.do_action(...args),
            do_notify: (...args) => this.do_notify(...args),
            do_warn: (...args) => this.do_warn(...args),
            rpc: (...args) => this._rpc(...args),
            trigger_up: (...args) => this.trigger_up(...args),
        };
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} [param0={}]
     * @param {boolean} [param0.withStore=true]
     * @return {Promise<Object>}
     */
    async get({ withStore=true }={}) {
        if (withStore) {
            const store = await this.call('store', 'get');
            return { store, ...this.env };
        }
        return { ...this.env };
    },
});

core.serviceRegistry.add('env', EnvService);

return EnvService;

});
