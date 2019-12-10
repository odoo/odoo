odoo.define('mail.messagingEnv', function (require) {
'use strict';

const actions = require('mail.store.actions');
const getters = require('mail.store.getters');
const initState = require('mail.store.state');

const env = require('web.env');
const webClient = require('web.web_client');

const { Store } = owl;

/**
 * Environment of the messaging store (messaging env. without store)
 */
const messagingStoreEnv = Object.create(env);
Object.assign(messagingStoreEnv, {
    disableAnimation: false,
    isDev: true,
    isTest: false,
    testServiceTarget: 'body',
    testStoreInitialState: {},
    call: (...args) => webClient.call(...args),
    do_action: (...args) => webClient.do_action(...args),
    do_notify: (...args) => webClient.do_notify(...args),
    do_warn: (...args) => webClient.do_warn(...args),
    rpc: (...args) => webClient._rpc(...args),
    trigger_up: (...args) => webClient.trigger_up(...args)
});

/**
 * Messaging store
 */
const store = new Store({
    actions,
    env: messagingStoreEnv,
    getters,
    state: initState(),
});

/**
 * Environment of messaging components (messaging env. with store)
 */
const messagingEnv = Object.create(messagingStoreEnv);
Object.assign(messagingEnv, { store });
store.dispatch('initMessaging');

window.env = messagingEnv;

return messagingEnv;

});
