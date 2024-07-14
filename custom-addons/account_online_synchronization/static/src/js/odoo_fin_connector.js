/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { cookie } from "@web/core/browser/cookie";
import { markup } from "@odoo/owl";
const actionRegistry = registry.category('actions');
/* global OdooFin, debugMode */

function OdooFinConnector(parent, action) {
    const orm = parent.services.orm;
    const actionService = parent.services.action;
    const notificationService = parent.services.notification;

    const id = action.id;
    action.params.colorScheme = cookie.get("color_scheme");
    let mode = action.params.mode || 'link';
    // Ensure that the proxyMode is valid
    const modeRegexp = /^[a-z0-9-_]+$/i;
    const runbotRegexp = /^https:\/\/[a-z0-9-_]+\.[a-z0-9-_]+\.odoo\.com$/i;
    if (!modeRegexp.test(action.params.proxyMode) && !runbotRegexp.test(action.params.proxyMode)) {
        return;
    }
    let url = 'https://' + action.params.proxyMode + '.odoofin.com/proxy/v1/odoofin_link';
    if (runbotRegexp.test(action.params.proxyMode)) {
        url = action.params.proxyMode + '/proxy/v1/odoofin_link';
    }
    let actionResult = false;

    loadJS(url)
        .then(function () {
            // Create and open the iframe
            const params = {
                data: action.params,
                proxyMode: action.params.proxyMode,
                onEvent: async function (event, data) {
                    switch (event) {
                        case 'close':
                            return;
                        case 'reload':
                            return actionService.doAction({type: 'ir.actions.client', tag: 'reload'});
                        case 'notification':
                            notificationService.add(data.message, data);
                            break;
                        case 'exchange_token':
                            await orm.call('account.online.link', 'exchange_token',
                                [[id], data], {context: action.context});
                            break;
                        case 'success':
                            mode = data.mode || mode;
                            actionResult = await orm.call('account.online.link', 'success', [[id], mode, data], {context: action.context});
                            actionResult.help = markup(actionResult.help)
                            return actionService.doAction(actionResult);
                        case 'connect_existing_account':
                            actionResult = await orm.call('account.online.link', 'connect_existing_account', [data], {context: action.context});
                            actionResult.help = markup(actionResult.help)
                            return actionService.doAction(actionResult);
                        default:
                            return;
                    }
                },
                onAddBank: async function () {
                    // If the user doesn't find his bank
                    actionResult = await orm.call('account.online.link', 'create_new_bank_account_action',
                    [], {context: action.context});
                    actionResult.help = markup(actionResult.help)
                    return actionService.doAction(actionResult);
                }
            };
            // propagate parent debug mode to iframe
            if(typeof debugMode !== 'undefined' && debugMode)
                params.data['debug'] = debugMode;
            OdooFin.create(params);
            OdooFin.open();
        });
    return;
}

actionRegistry.add('odoo_fin_connector', OdooFinConnector);

export default OdooFinConnector;
