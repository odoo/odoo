/** @odoo-module **/

import DialogManager from '@mail/components/dialog_manager/dialog_manager';

import AbstractService from 'web.AbstractService';
import { bus, serviceRegistry } from 'web.core';

const components = { DialogManager };

const DialogService = AbstractService.extend({
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
        const DialogManagerComponent = components.DialogManager;
        this.component = new DialogManagerComponent(null);
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

export default DialogService;
