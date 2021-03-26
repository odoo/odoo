/** @odoo-module **/

import ChatWindowManager from '@mail/components/chat_window_manager/chat_window_manager';

import AbstractService from 'web.AbstractService';
import { bus, serviceRegistry } from 'web.core';

const components = { ChatWindowManager };

const ChatWindowService = AbstractService.extend({
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super(...arguments);
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
     * @returns {Node}
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
        const ChatWindowManagerComponent = components.ChatWindowManager;
        this.component = new ChatWindowManagerComponent(null);
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
});

serviceRegistry.add('chat_window', ChatWindowService);

export default ChatWindowService;
