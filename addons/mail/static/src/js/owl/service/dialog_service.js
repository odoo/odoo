odoo.define('mail.service.Dialog', function (require) {
"use strict";

const DialogManager = require('mail.component.DialogManager');
const EnvMixin = require('mail.widget.EnvMixin');

const AbstractService = require('web.AbstractService');
const core = require('web.core');

const DEBUG = true;

const DialogService = AbstractService.extend(EnvMixin, {
    TEST_ENV: {
        active: false,
    },
    dependencies: ['env', 'store'],
    /**
     * @override {web.AbstractService}
     */
    init() {
        this._super.apply(this, arguments);
        this._webClientReady = false;
        if (DEBUG) {
            window.dialog_service = this;
        }
    },
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super.apply(this, arguments);
        if (!this.TEST_ENV.active) {
            core.bus.on('hide_home_menu', this, this._onHideHomeMenu.bind(this));
            core.bus.on('show_home_menu', this, this._onShowHomeMenu.bind(this));
            core.bus.on('web_client_ready', this, this._onWebClientReady.bind(this));
        } else {
            this['test:hide_home_menu'] = this._onHideHomeMenu;
            this['test:show_home_menu'] = this._onShowHomeMenu;
            this['test:web_client_ready'] = this._onWebClientReady;
        }
    },
    /**
     * @private
     */
    destroy() {
        if (this.component) {
            this.component.destroy();
            this.component = undefined;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _mount() {
        if (this.component) {
            this.component.destroy();
            this.component = undefined;
        }
        if (!this.env) {
            await this.getEnv();
        }
        this.component = new DialogManager(this.env);
        let parentNode;
        if (this.TEST_ENV.active) {
            parentNode = document.querySelector(this.TEST_ENV.container);
        } else {
            parentNode = document.querySelector('body');
        }
        await this.component.mount(parentNode);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _onHideHomeMenu() {
        if (!this._webClientReady) {
            return;
        }
        if (document.querySelector('.o_DialogManager')) {
            return;
        }
        await this._mount();
    },
    async _onShowHomeMenu() {
        if (!this._webClientReady) {
            return;
        }
        if (document.querySelector('.o_DialogManager')) {
            return;
        }
        await this._mount();
    },
    /**
     * @private
     */
    async _onWebClientReady() {
        await this._mount();
        this._webClientReady = true;
    }
});

core.serviceRegistry.add('dialog', DialogService);

return DialogService;

});
