odoo.define('mail.service.Dialog', function (require) {
'use strict';

const DialogManager = require('mail.component.DialogManager');

const AbstractService = require('web.AbstractService');
const { bus, serviceRegistry } = require('web.core');

const DialogService = AbstractService.extend({
    dependencies: ['messaging'],
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super(...arguments);
        this.env = this.call('messaging', 'getMessagingEnv');
        this._webClientReady = false;
        this._listenHomeMenu();
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
     * @return {Node}
     */
    _getParentNode() {
        return document.querySelector('body');
    },
    /**
     * @private
     */
    _listenHomeMenu() {
        bus.on('hide_home_menu', this, this._onHideHomeMenu.bind(this));
        bus.on('show_home_menu', this, this._onShowHomeMenu.bind(this));
        bus.on('web_client_ready', this, this._onWebClientReady.bind(this));
    },
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
        const parentNode = this._getParentNode();
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
