odoo.define('mail.service.Dialog', function (require) {
'use strict';

const DialogManager = require('mail.component.DialogManager');
const OwlMixin = require('mail.widget.OwlMixin');

const AbstractService = require('web.AbstractService');
const { bus, serviceRegistry } = require('web.core');

const DialogService = AbstractService.extend(OwlMixin, {
    IS_DEV: true,
    /**
     * This is set when dialog service is used in a test environment.
     * Useful to prevent sending and/or receiving events from
     * core.bus.
     */
    IS_TEST: false,
    TEST_TARGET: 'body',
    dependencies: ['owl'],
    /**
     * @override {web.AbstractService}
     */
    init() {
        this._super(...arguments);
        this._webClientReady = false;
        DialogManager.env = OwlMixin.getEnv.call(this);
        if (this.IS_DEV) {
            window.dialog_service = this;
        }
    },
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super(...arguments);
        if (!this.IS_TEST) {
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
        this.component = new DialogManager(null);
        let parentNode;
        if (this.IS_TEST) {
            parentNode = document.querySelector(this.TEST_TARGET);
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
