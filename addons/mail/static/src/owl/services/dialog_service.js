odoo.define('mail.service.Dialog', function (require) {
'use strict';

const DialogManager = require('mail.component.DialogManager');
const messagingEnv = require('mail.messagingEnv');

const AbstractService = require('web.AbstractService');
const { bus, serviceRegistry } = require('web.core');

const DialogService = AbstractService.extend({
    env: messagingEnv,
    /**
     * @override {web.AbstractService}
     */
    init() {
        this._super(...arguments);
        this._webClientReady = false;
        if (this.env.isDev) {
            window.dialog_service = this;
        }
    },
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super(...arguments);
        if (!this.env.isTest) {
            bus.on('hide_home_menu', this, this._onHideHomeMenu.bind(this));
            bus.on('show_home_menu', this, this._onShowHomeMenu.bind(this));
            bus.on('web_client_ready', this, this._onWebClientReady.bind(this));
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
        DialogManager.env = this.env;
        this.component = new DialogManager(null);
        let parentNode;
        if (this.env.isTest) {
            parentNode = document.querySelector(this.env.TEST_SERVICE_TARGET);
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

serviceRegistry.add('dialog', DialogService);

return DialogService;

});
