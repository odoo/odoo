odoo.define('mail.messagingTestEnv', function (require) {
'use strict';

const ChatWindowService = require('mail.service.ChatWindow');
const DialogService = require('mail.service.Dialog');
const actions = require('mail.store.actions');
const getters = require('mail.store.getters');
const initState = require('mail.store.state');
const DiscussWidget = require('mail.widget.Discuss');
const MessagingMenuWidget = require('mail.widget.MessagingMenu');

const makeTestEnvironment = require('web.test_env');

const { Store } = owl;

/**
 * @param {web.Widget} widget not necessarily in DOM yet, but should be when in use.
 * @param {Object} [param1={}]
 * @param {boolean} [param1.debug=false]
 * @param {function} [param1.providedRPC]
 * @param {function} [param1.session]
 * @return {Object} the messaging test environment
 */
function makeMessagingTestEnvironment(widget, {
    debug = false,
    providedRPC,
    session,
}={}) {
    const _t = s => s;
    _t.database = { parameters: { direction: 'ltr' } };
    const env = makeTestEnvironment({
        _t,
        session: Object.assign({
            is_bound: Promise.resolve(),
            name: 'Admin',
            partner_display_name: 'Mitchell Admin',
            partner_id: 3,
            url: s => s,
            userId: 2,
        }, session),
    }, providedRPC);

    /**
     * Environment of the messaging store (messaging env. without store)
     */
    const messagingStoreEnv = Object.create(env);
    Object.assign(messagingStoreEnv, {
        disableAnimation: true,
        isDev: true,
        isTest: true,
        testServiceTarget: debug ? 'body' : '#qunit-fixture',
        testStoreInitialState: {},
        call: (...args) => widget.call(...args),
        do_action: (...args) => widget.do_action(...args),
        do_notify: (...args) => widget.do_notify(...args),
        do_warn: (...args) => widget.do_warn(...args),
        rpc: (...args) => widget._rpc(...args),
        trigger_up: (...args) => widget.trigger_up(...args),
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
    // disable auto-fetch partner im status
    store.actions._startLoopFetchPartnerImStatus = () => {};
    store.actions._loopFetchPartnerImStatus = () => {};
    store.dispatch('initMessaging');

    /**
     * Environment of top-level messaging components (messaging env. with store)
     */
    const messagingTestEnv = Object.create(messagingStoreEnv);
    Object.assign(messagingTestEnv, { store });

    /**
     * Widgets pass env to top-level messaging components
     */
    ChatWindowService.prototype.env = messagingTestEnv;
    DialogService.prototype.env = messagingTestEnv;
    DiscussWidget.prototype.env = messagingTestEnv;
    MessagingMenuWidget.prototype.env = messagingTestEnv;

    return messagingTestEnv;
}

return makeMessagingTestEnvironment;

});
