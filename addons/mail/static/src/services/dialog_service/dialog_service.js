/** @odoo-module **/

import { getMessagingComponent } from "@mail/utils/messaging_component";

import AbstractService from 'web.AbstractService';
import { bus } from 'web.core';

const { App } = owl;

export const DialogService = AbstractService.extend({
    dependencies: ['messaging'],
    /**
     * @override {web.AbstractService}
     */
    start() {
        this._super(...arguments);
        this._listenHomeMenu();
    },
    /**
     * @private
     */
    destroy() {
        if (this.app) {
            this.app.destroy();
            this.app = undefined;
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
        bus.on('web_client_ready', this, this._onWebClientReady.bind(this));
    },
    /**
     * @private
     */
    async _mount() {
        if (this.app) {
            this.app.destroy();
            this.app = undefined;
        }
        const DialogManagerComponent = getMessagingComponent("DialogManager");
        this.app = new App(DialogManagerComponent, {
            env: owl.Component.env,
            templates: window.__ODOO_TEMPLATES__,
        });
        const parentNode = this._getParentNode();
        await this.app.mount(parentNode);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _onWebClientReady() {
        await this._mount();
    }
});
