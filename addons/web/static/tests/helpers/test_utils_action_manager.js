odoo.define('web.test_utils_action_manager', function (require) {
"use strict";

const WebClient = require('web.WebClient');
const testUtilsAsync = require('web.test_utils_async');

async function doAction(action, options) {
    WebClient.env.bus.trigger('do-action', {action, options});
    await testUtilsAsync.owlCompatibilityExtraNextTick();
    return testUtilsAsync.nextTick();
}

async function loadState(webClient, state) {
    webClient._getWindowHash = () => {
        const hash = Object.keys(state).map(k => `${k}=${state[k]}`).join('&');
        return `#${hash}`;
    };
    webClient._onHashchange();
    await testUtilsAsync.owlCompatibilityExtraNextTick();
    return testUtilsAsync.nextTick();
}

return {
    doAction: doAction,
    loadState: loadState,
};

});
