odoo.define('mail/static/src/env/test_env.js', function (require) {
'use strict';

const ModelManager = require('mail/static/src/model/model_manager.js');
const { makeDeferred } = require('mail/static/src/utils/deferred/deferred.js');
const { nextTick } = require('mail/static/src/utils/utils.js');

const { Store } = owl;
const { EventBus } = owl.core;

/**
 * @param {Object} [providedEnv={}]
 * @returns {Object}
 */
function addMessagingToEnv(providedEnv = {}) {

    const defaultEnv = Object.assign({}, providedEnv, {
        session: Object.assign({
            is_bound: Promise.resolve(),
            name: 'Admin',
            partner_display_name: 'Your Company, Admin',
            partner_id: 3,
            uid: 2,
            url: s => s,
        }, providedEnv.session)
    });

    let env = Object.assign({
        loadingBaseDelayDuration: defaultEnv.loadingBaseDelayDuration || 0,
    }, defaultEnv);

    /**
     * Messaging store
     */
    const store = new Store({
        env,
        state: {},
    });

    /**
     * Registry of models.
     */
    env.models = {};
    /**
     * Environment keys used in messaging.
     */
    Object.assign(env, {
        autofetchPartnerImStatus: false,
        browser: Object.assign({
            innerHeight: 1080,
            innerWidth: 1920,
            Notification: Object.assign({
                permission: 'denied',
                async requestPermission() {
                    return this.permission;
                },
            }, (env.browser && env.browser.Notification) || {}),
        }, env.browser),
        destroyMessaging() {
            if (env.modelManager) {
                env.modelManager.deleteAll();
                env.messaging = undefined;
            }
        },
        disableAnimation: true,
        isMessagingInitialized() {
            if (!this.messaging) {
                return false;
            }
            return this.messaging.isInitialized;
        },
        messaging: undefined,
        messagingInitializedDeferred: makeDeferred(),
        messagingBus: new EventBus(),
        modelManager: new ModelManager(),
        store,
    });

    return env;
}

/**
 * @param {Object} [providedEnv={}]
 * @returns {Object}
 */
function addTimeControlToEnv(providedEnv = {}) {

    let env = Object.assign({}, providedEnv);

    if (!env.browser) {
        env.browser = {};
    }
    // list of timeout ids that have timed out.
    let timedOutIds = [];
    // key: timeoutId, value: func + remaining duration
    const timeouts = new Map();
    Object.assign(env.browser, {
        clearTimeout: id => {
            timeouts.delete(id);
            timedOutIds = timedOutIds.filter(i => i !== id);
        },
        setTimeout: (func, duration) => {
            const timeoutId = _.uniqueId('timeout_');
            const timeout = {
                id: timeoutId,
                isTimedOut: false,
                func,
                duration,
            };
            timeouts.set(timeoutId, timeout);
            if (duration === 0) {
                timedOutIds.push(timeoutId);
                timeout.isTimedOut = true;
            }
            return timeoutId;
        },
    });
    if (!env.testUtils) {
        env.testUtils = {};
    }
    Object.assign(env.testUtils, {
        advanceTime: async duration => {
            await nextTick();
            for (const id of timeouts.keys()) {
                const timeout = timeouts.get(id);
                if (timeout.isTimedOut) {
                    continue;
                }
                timeout.duration = Math.max(timeout.duration - duration, 0);
                if (timeout.duration === 0) {
                    timedOutIds.push(id);
                }
            }
            while (timedOutIds.length > 0) {
                const id = timedOutIds.shift();
                const timeout = timeouts.get(id);
                timeouts.delete(id);
                timeout.func();
                await nextTick();
            }
            await nextTick();
        },
    });
    return env;
}

return {
    addMessagingToEnv,
    addTimeControlToEnv,
};

});
