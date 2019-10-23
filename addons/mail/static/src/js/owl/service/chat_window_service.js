odoo.define('mail.service.ChatWindowService', function (require) {
'use strict';

const ChatWindowManager = require('mail.component.ChatWindowManager');
const EnvMixin = require('mail.widget.EnvMixin');

const AbstractService = require('web.AbstractService');
const core = require('web.core');

const ChatWindowService = AbstractService.extend(EnvMixin, {
    DEBUG: true,
    TEST_ENV: {
        active: false,
        container: 'body',
    },
    dependencies: ['env', 'store'],
    init() {
        this._super.apply(this, arguments);
        this._webClientReady = false;
        if (this.DEBUG) {
            window.chat_window_service = this;
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
            core.bus.on('will_hide_home_menu', this, this._onWillHideHomeMenu.bind(this));
            core.bus.on('will_show_home_menu', this, this._onWillShowHomeMenu.bind(this));
        } else {
            this['test:hide_home_menu'] = this._onHideHomeMenu;
            this['test:show_home_menu'] = this._onShowHomeMenu;
            this['test:web_client_ready'] = this._onWebClientReady;
            this['test:will_hide_home_menu'] = this._onWillHideHomeMenu;
            this['test:will_show_home_menu'] = this._onWillShowHomeMenu;
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
        await this.getEnv();
        if (this.component) {
            this.component.destroy();
            this.component = undefined;
        }
        this.component = new ChatWindowManager(this.env);
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
        if (document.querySelector('.o_ChatWindowManager')) {
            return;
        }
        await this._mount();
    },
    /**
     * @private
     */
    async _onShowHomeMenu() {
        if (!this._webClientReady) {
            return;
        }
        if (document.querySelector('.o_ChatWindowManager')) {
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
    },
    /**
     * @private
     */
    async _onWillHideHomeMenu() {
        if (this.component) {
            this.component.saveChatWindowsStates();
        }
    },
    /**
     * @private
     */
    async _onWillShowHomeMenu() {
        if (this.component) {
            this.component.saveChatWindowsStates();
        }
    },
});

core.serviceRegistry.add('chat_window', ChatWindowService);

return ChatWindowService;

});
