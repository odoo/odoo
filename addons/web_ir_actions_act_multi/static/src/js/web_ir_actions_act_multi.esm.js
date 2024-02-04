/** @odoo-module **/

import {registry} from "@web/core/registry";

/**
 * Handle 'ir.actions.act_multi' action
 * @param {object} action see _handleAction() parameters
 * @returns {$.Promise}
 */

async function executeMultiAction({env, action}) {
    return action.actions
        .map((item) => {
            return () => {
                return env.services.action.doAction(item);
            };
        })
        .reduce((prev, cur) => {
            return prev.then(cur);
        }, Promise.resolve());
}

registry.category("action_handlers").add("ir.actions.act_multi", executeMultiAction);
