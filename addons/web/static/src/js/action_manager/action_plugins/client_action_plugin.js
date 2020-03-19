odoo.define('web.ClientActionPlugin', function (require) {
    "use strict";

    /**
     * The purpose of this file is to add the support of Odoo actions of type
     * 'ir.actions.report' to the ActionManager.
     */

    const AbstractActionPlugin = require('web.AbstractActionPlugin');
    const ActionManager = require('web.ActionManager');
    const { action_registry } = require('web.core');
    const { Component } = owl;
    const Widget = require('web.Widget');

    class ClientActionPlugin extends AbstractActionPlugin {
    /**
     * Executes actions of type 'ir.actions.client'.
     *
     * @param {Object} action the description of the action to execute
     * @param {string} action.tag the key of the action in the action_registry
     * @param {Object} options @see doAction for details
     */
    async executeAction(action, options) {
        const ClientAction = action_registry.get(action.tag);
        if (!ClientAction) {
            console.error(`Could not find client action ${action.tag}`, action);
            return Promise.reject();
        } else {
            const proto = ClientAction.prototype;
            if (!(proto instanceof Component) && !(proto instanceof Widget)) {
                // the client action might be a function, which is executed and
                // whose returned value might be another action to execute
                const nextAction = ClientAction(this.env, action);
                if (nextAction) {
                    action = nextAction;
                    return this.doAction(action);
                }
                return;
            }
        }
        const params = Object.assign({}, options, {Component: ClientAction});
        const controller = this.makeBaseController(action, params);
        options.controllerID = controller.jsID;
        controller.options = options;
        action.id = action.id || action.tag;
        this.pushControllers([controller]);
    }
    /**
     * @override
     */
    loadState(state, options) {
        if (typeof state.action === 'string' && action_registry.contains(state.action)) {
            const action = {
                params: state,
                tag: state.action,
                type: 'ir.actions.client',
            };
            return this.doAction(action, options);
        }
    }
}
ClientActionPlugin.type = 'ir.actions.client';

ActionManager.registerPlugin(ClientActionPlugin);

return ClientActionPlugin;
});