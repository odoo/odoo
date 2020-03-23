odoo.define('web.UrlActionPlugin', function (require) {
    "use strict";

    /**
     * The purpose of this file is to add the support of Odoo actions of type
     * 'ir.actions.act_window' to the ActionManager.
     */
    const ActionAbstractPlugin = require('web.ActionAbstractPlugin');
    const ActionManager = require('web.ActionManager');
    const { redirect } = require('web.framework');

    class UrlActionPlugin extends ActionAbstractPlugin {
        /**
         * Executes actions of type 'ir.actions.act_url', i.e. redirects to the
         * given url.
         *
         * @param {Object} action the description of the action to execute
         * @param {string} action.url
         * @param {string} [action.target] set to 'self' to redirect in the current page,
         *   redirects to a new page by default
         * @param {Object} options @see doAction for details
         */
        async executeAction(action, options) {
            if (action.target === 'self') {
                redirect(action.url);
            } else {
                const w = window.open(action.url, '_blank');
                if (!w || w.closed || typeof w.closed === 'undefined') {
                    const message = this.env._t('A popup window has been blocked. You ' +
                        'may need to change your browser settings to allow ' +
                        'popup windows for this page.');
                    this.env.services.notification.notify({
                        title: this.env._t('Warning'),
                        type: 'danger',
                        message: message,
                        sticky: true,
                    });
                }
                options.on_close();
            }
        }
    }
    UrlActionPlugin.type = 'ir.actions.act_url';

    ActionManager.registerPlugin(UrlActionPlugin);

    return UrlActionPlugin;
});