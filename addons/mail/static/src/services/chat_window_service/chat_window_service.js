/** @odoo-module **/

// ensure component is registered beforehand.
import '@mail/components/chat_window_manager/chat_window_manager';
import { getMessagingComponent } from "@mail/utils/messaging_component";

import AbstractService from 'web.AbstractService';
import { bus } from 'web.core';

const { App } = owl;

export const ChatWindowService = AbstractService.extend({
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
        const ChatWindowManagerComponent = getMessagingComponent("ChatWindowManager");
        this.app = new App(ChatWindowManagerComponent, {
            templates: window.__OWL_TEMPLATES__,
            env: owl.Component.env,
            dev: owl.Component.env.isDebug(),
            translateFn: owl.Component.env._t,
            translatableAttributes: ["data-tooltip"],
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
    },
});
