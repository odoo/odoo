odoo.define('web.ServerActionPlugin', function (require) {
    "use strict";

    /**
     * The purpose of this file is to add the support of Odoo actions of type
     * 'ir.actions.report' to the ActionManager.
     */

    const AbstractActionPlugin = require('web.AbstractActionPlugin');
    const ActionManager = require('web.ActionManager');

    class ServerActionPlugin extends AbstractActionPlugin {
        /**
         * Executes actions of type 'ir.actions.server'.
         *
         * @param {Object} action the description of the action to execute
         * @param {integer} action.id the db ID of the action to execute
         * @param {Object} [action.context]
         * @param {Object} options @see doAction for details
         * @returns {Promise} resolved when the action has been executed
         */
        async executeAction(action, options) {
            action = await this.rpc({
                route: '/web/action/run',
                params: {
                    action_id: action.id,
                    context: action.context || {},
                },
            });
            action = action || { type: 'ir.actions.act_window_close' };
            return this.actionManager.doAction(action, options);
        }
    }
    ServerActionPlugin.type = 'ir.actions.server';

    ActionManager.registerPlugin(ServerActionPlugin);

    return ServerActionPlugin;
});