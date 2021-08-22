/** @odoo-module **/

import BusService from 'bus.BusService';

import { messagingService, messagingValues } from '@mail/services/messaging_service/messaging_service';
import { newMessageService } from "@mail/services/new_message_service/new_message_service";
import { getMessagingComponent } from '@mail/utils/messaging_component';
import { nextTick } from '@mail/utils/utils';
import { MockModels } from '@mail/../tests/helpers/mock_models';

import AbstractStorageService from 'web.AbstractStorageService';
import { browser } from "@web/core/browser/browser";
import { registry } from '@web/core/registry';
import { commandService } from "@web/webclient/commands/command_service";
import RamStorage from 'web.RamStorage';
import { makeTestPromise } from 'web.test_utils';
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient, getActionManagerServerData } from "@web/../tests/webclient/helpers";
import LegacyRegistry from "web.Registry";

const { EventBus } = owl.core;

//------------------------------------------------------------------------------
// Private
//------------------------------------------------------------------------------

/**
 * Create a fake object 'dataTransfer', linked to some files,
 * which is passed to drag and drop events.
 *
 * @param {Object[]} files
 * @returns {Object}
 */
function _createFakeDataTransfer(files) {
    return {
        dropEffect: 'all',
        effectAllowed: 'all',
        files,
        items: [],
        types: ['Files'],
    };
}

//------------------------------------------------------------------------------
// Public: rendering timers
//------------------------------------------------------------------------------

/**
 * Returns a promise resolved at the next animation frame.
 *
 * @returns {Promise}
 */
function nextAnimationFrame() {
    const requestAnimationFrame = owl.Component.scheduler.requestAnimationFrame;
    return new Promise(function (resolve) {
        setTimeout(() => requestAnimationFrame(() => resolve()));
    });
}

/**
 * Returns a promise resolved the next time OWL stops rendering.
 *
 * @param {function} func function which, when called, is
 *   expected to trigger OWL render(s).
 * @param {number} [timeoutDelay=5000] in ms
 * @returns {Promise}
 */
const afterNextRender = (function () {
    const stop = owl.Component.scheduler.stop;
    const stopPromises = [];

    owl.Component.scheduler.stop = function () {
        const wasRunning = this.isRunning;
        stop.call(this);
        if (wasRunning) {
            while (stopPromises.length) {
                stopPromises.pop().resolve();
            }
        }
    };

    async function afterNextRender(func, timeoutDelay = 5000) {
        // Define the potential errors outside of the promise to get a proper
        // trace if they happen.
        const startError = new Error("Timeout: the render didn't start.");
        const stopError = new Error("Timeout: the render didn't stop.");
        // Set up the timeout to reject if no render happens.
        let timeoutNoRender;
        const timeoutProm = new Promise((resolve, reject) => {
            timeoutNoRender = setTimeout(() => {
                let error = startError;
                if (owl.Component.scheduler.isRunning) {
                    error = stopError;
                }
                console.error(error);
                reject(error);
            }, timeoutDelay);
        });
        // Set up the promise to resolve if a render happens.
        const prom = makeTestPromise();
        stopPromises.push(prom);
        // Start the function expected to trigger a render after the promise
        // has been registered to not miss any potential render.
        const funcRes = func();
        // Make them race (first to resolve/reject wins).
        await Promise.race([prom, timeoutProm]);
        clearTimeout(timeoutNoRender);
        // Wait the end of the function to ensure all potential effects are
        // taken into account during the following verification step.
        await funcRes;
        // Wait one more frame to make sure no new render has been queued.
        await nextAnimationFrame();
        if (owl.Component.scheduler.isRunning) {
            await afterNextRender(() => {}, timeoutDelay);
        }
        return funcRes;
    }

    return afterNextRender;
})();

function getAfterEvent(messagingBus) {
    /**
     * Returns a promise resolved after the expected event is received.
     *
     * @param {Object} param0
     * @param {string} param0.eventName event to wait
     * @param {function} param0.func function which, when called, is expected to
     *  trigger the event
     * @param {string} [param0.message] assertion message
     * @param {function} [param0.predicate] predicate called with event data.
     *  If not provided, only the event name has to match.
     * @param {number} [param0.timeoutDelay=5000] how long to wait at most in ms
     * @returns {Promise}
     */
    return async function afterEvent({ eventName, func, message, predicate, timeoutDelay = 5000 }) {
        // Set up the timeout to reject if the event is not triggered.
        let timeoutNoEvent;
        const timeoutProm = new Promise((resolve, reject) => {
            timeoutNoEvent = setTimeout(() => {
                let error = message
                    ? new Error(message)
                    : new Error(`Timeout: the event ${eventName} was not triggered.`);
                console.error(error);
                reject(error);
            }, timeoutDelay);
        });
        // Set up the promise to resolve if the event is triggered.
        const eventProm = new Promise(resolve => {
            messagingBus.on(eventName, null, data => {
                if (!predicate || predicate(data)) {
                    resolve();
                }
            });
        });
        // Start the function expected to trigger the event after the
        // promise has been registered to not miss any potential event.
        const funcRes = func();
        // Make them race (first to resolve/reject wins).
        await Promise.race([eventProm, timeoutProm]);
        clearTimeout(timeoutNoEvent);
        return funcRes;
    };
}

//------------------------------------------------------------------------------
// Public: test lifecycle
//------------------------------------------------------------------------------

function beforeEach() {
    // Warnings to ease migration of code / future rebase.
    Object.defineProperty(this, 'advanceTime', {
        get() {
            throw Error("don't use this.advanceTime, use advanceTime from start() instead");
        },
    });
    Object.defineProperty(this, 'afterEvent', {
        get() {
            throw Error("don't use this.afterEvent, use afterEvent from start() instead");
        },
    });
    Object.defineProperty(this, 'data', {
        get() {
            throw Error('use this.serverData instead of this.data (it has extra keys, you might want to update this.serverData.models in particular?)');
        },
    });
    Object.defineProperty(this, 'env', {
        get() {
            throw Error("don't use this.env, use env from start() instead (or directly messaging from start() maybe?)");
        },
    });
    Object.defineProperty(this, 'messaging', {
        get() {
            throw Error("don't use this.messaging, use messaging from start() instead");
        },
    });
    Object.defineProperty(this, 'widget', {
        get() {
            throw Error("don't use this.widget, use webClient from start() instead");
        },
    });

    const serverData = MockModels.generateServerData();
    Object.assign(this, { serverData });

    this.start = async (params = {}) => {
        if (params.serverData) {
            throw Error("don't give serverData to start, update this.serverData instead");
        }
        const result = await start({
            ...params,
            serverData: this.serverData,
        });
        this.webClient = result.webClient;
        return result;
    };
}

function afterEach() {
    throw Error("afterEach should no longer be called");
}

/**
 * Creates and returns a new root Component with the given props and mounts it
 * on target.
 * Assumes that self.env is set to the correct value.
 * Components created this way are automatically registered for clean up after
 * the test, which will happen when `afterEach` is called.
 *
 * @param {Object} self the current QUnit instance
 * @param {string} componentName the class name of the component to create
 * @param {Object} param2
 * @param {Object} [param2.props={}] forwarded to component constructor
 * @param {DOM.Element} param2.target mount target for the component
 * @returns {owl.Component} the new component instance
 */
async function createRootMessagingComponent(self, componentName, { props = {}, target }) {
    // todo replace by actually using main component stuff from webclient
    const Component = getMessagingComponent(componentName);
    Component.env = self.webClient.env;
    const component = new Component(null, props);
    delete Component.env;
    await afterNextRender(() => component.mount(target));
    registerCleanup(() => component.destroy());
    return component;
}


function getTimeControl() {
    // list of timeout ids that have timed out.
    let timedOutIds = [];
    // key: timeoutId, value: func + remaining duration
    const timeouts = new Map();
    patchWithCleanup(browser, {
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
    return async function (duration) {
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
    };
}

function getOpenDiscuss({ afterEvent, env }) {
    return async function openDiscuss({ activeId = 'mail.box_inbox', waitUntilMessagesLoaded = true, waitUntilScrollToEnd = false } = {}) {
        function openDiscussAction() {
            return env.services.action.doAction({
                id: 200001,
                params: { 'default_active_id': activeId },
                tag: "mail.widgets.discuss",
                type: "ir.actions.client",
                xml_id: "mail.action_discuss",
            });
        }
        return afterNextRender(() => {
            const [model, id] = typeof activeId === 'number' ? ['mail.channel', activeId] : activeId.split('_');
            if (waitUntilScrollToEnd) {
                return afterEvent({
                    eventName: 'o-component-message-list-scrolled',
                    func: () => openDiscussAction(),
                    message: `should wait until ${model} ${id} scrolled to its last message initially`,
                    predicate: ({ scrollTop, thread }) => {
                        const messageList = document.querySelector('.o_ThreadView_messageList');
                        return (
                            thread &&
                            thread.model === model &&
                            thread.id.toString() === id &&
                            scrollTop === messageList.scrollHeight - messageList.clientHeight
                        );
                    },
                });
            }
            if (waitUntilMessagesLoaded) {
                return afterEvent({
                    eventName: 'o-thread-view-hint-processed',
                    func: () => openDiscussAction(),
                    message: `should wait until ${model} ${id} displayed its messages`,
                    predicate: ({ hint, threadViewer }) => {
                        return (
                            hint.type === 'messages-loaded' &&
                            threadViewer.thread.model === model &&
                            threadViewer.thread.id.toString() === id
                        );
                    },
                });
            }
            return openDiscussAction();
        });
    };
}

/**
 * Main function used to make a mocked environment with mocked messaging env.
 *
 * @param {Object} [param0={}]
 * @param {function} [param0.mockRPC]
 * @param {boolean} [param0.hasDiscuss=false] if set, mount discuss app.
 * @param {boolean} [param0.hasTimeControl=false] if set, all flow of time
 *   with `env.browser.setTimeout` are fully controlled by test itself.
 *     @see addTimeControlToEnv that adds `advanceTime` function in
 *     `env.testUtils`.
 * @param {integer} [param0.loadingBaseDelayDuration=0]
 * @param {Deferred|Promise} [param0.messagingBeforeCreationDeferred=Promise.resolve()]
 *   Deferred that let tests block messaging creation and simulate resolution.
 *   Useful for testing working components when messaging is not yet created.
 * @param {Object} [param0.services]
 * @param {Object} [param0.waitUntilEvent]
 * @param {String} [param0.waitUntilEvent.eventName]
 * @param {String} [param0.waitUntilEvent.message]
 * @param {function} [param0.waitUntilEvent.predicate]
 * @param {integer} [param0.waitUntilEvent.timeoutDelay]
 * @param {string} [param0.waitUntilMessagingCondition='initialized'] Determines
 *   the condition of messaging when this function is resolved.
 *   Supported values: ['none', 'created', 'initialized'].
 *   - 'none': the function resolves regardless of whether messaging is created.
 *   - 'created': the function resolves when messaging is created, but
 *     regardless of whether messaging is initialized.
 *   - 'initialized' (default): the function resolves when messaging is
 *     initialized.
 *   To guarantee messaging is not created, test should pass a pending deferred
 *   as param of `messagingBeforeCreationDeferred`. To make sure messaging is
 *   not initialized, test should mock RPC `mail/init_messaging` and block its
 *   resolution.
 * @throws {Error} in case some provided parameters are wrong, such as
 *   `waitUntilMessagingCondition`.
 * @returns {Object}
 */
async function start(param0 = {}) {
    // Warnings to ease migration of code / future rebase.
    if (param0.actions) {
        throw Error("don't give actions to start(), give serverData.actions");
    }
    if (param0.archs) {
        throw Error("don't give archs to start(), give serverData.views");
    }
    if (param0.data) {
        throw Error("don't give data to start(), give serverData");
    }
    if (param0.debug) {
        throw Error("don't give debug to start(), define test with QUnit.debug");
    }
    if (param0.discuss) {
        throw Error("don't give discuss to start(), use openDiscuss() params");
    }
    if (param0.env) {
        throw Error("don't give env to start(), give legacyEnv");
    }
    if (param0.kwargs) {
        throw Error("don't give kwargs to start()");
    }
    if (param0.hasDiscuss) {
        throw Error("don't give hasDiscuss to start(), call startWithDiscuss() instead");
    }
    if (param0.session) {
        throw Error("don't give session to start()");
    }
    const {
        browser: browserValues = {},
        legacyEnv,
        legacyServices,
        hasTimeControl = false,
        loadingBaseDelayDuration = 0,
        messagingBeforeCreationDeferred = Promise.resolve(),
        mockRPC,
        serverData = {},
        services,
        waitUntilEvent,
        waitUntilMessagingCondition = 'initialized',
    } = param0;
    if (!['none', 'created', 'initialized'].includes(waitUntilMessagingCondition)) {
        throw Error(`Unknown parameter value ${waitUntilMessagingCondition} for 'waitUntilMessaging'.`);
    }
    const originals = {
        '_.debounce': _.debounce,
        '_.throttle': _.throttle,
    };
    (function patch() {
        // patch _.debounce and _.throttle to be fast and synchronous
        _.debounce = _.identity;
        _.throttle = _.identity;
    })();
    registerCleanup(function unpatch() {
        _.debounce = originals['_.debounce'];
        _.throttle = originals['_.throttle'];
    });
    const messagingBus = new EventBus();
    patchWithCleanup(browser, {
        Notification: {
            permission: 'denied',
            async requestPermission() {
                return this.permission;
            },
        },
        ...browserValues
    });
    patchWithCleanup(messagingValues, {
        autofetchPartnerImStatus: false,
        disableAnimation: true,
        isQUnitTest: true,
        loadingBaseDelayDuration,
        messagingBus,
    });
    patchWithCleanup(messagingService, {
        async _startModelManager() {
            const _super = this._super.bind(this);
            await messagingBeforeCreationDeferred;
            return _super();
        }
    });
    for (const service in services) {
        registry.category('services').add(service, services[service]);
    }
    registry.category('services').add("command", commandService);
    registry.category('services').add('messaging', messagingService);
    registry.category('services').add("new_message", newMessageService);
    registry.category('systray').add('mail.messaging_menu', {
        Component: getMessagingComponent('MessagingMenu'),
        props: {},
    }, { sequence: 5 });
    registry.category('main_components').add('mail.chat_window_manager', {
        Component: getMessagingComponent('ChatWindowManager'),
        props: {},
    });
    registry.category('main_components').add('mail.dialog', {
        Component: getMessagingComponent('DialogManager'),
        props: {},
    });
    registry.category("command_categories").add("default", { label: ("default") });
    registry.category("actions").add("mail.widgets.discuss", getMessagingComponent('Discuss'));
    const legacyServiceRegistry = new LegacyRegistry();
    legacyServiceRegistry.add('bus_service', BusService.extend({
        _beep() {},
        _poll() {},
        _registerWindowUnload() {},
        isOdooFocused() {
            return true;
        },
        updateOption() {},
    }));
    legacyServiceRegistry.add('local_storage', AbstractStorageService.extend({
        storage: new RamStorage(),
    }));
    for (const legacyService in legacyServices) {
        legacyServiceRegistry.add(legacyService, legacyServices[legacyService]);
    }
    const legacyParams = {
        // ...kwargs, // todo what is it supposed to be?
        env: legacyEnv,
        serviceRegistry: legacyServiceRegistry,
        withLegacyMockServer: true,
    };
    const actionManagerServerData = getActionManagerServerData();
    const afterEvent = getAfterEvent(messagingBus);
    async function getWebClient() {
        return afterNextRender(async () => {
            const finalServerData = {
                ...actionManagerServerData,
                ...serverData,
                actions: {
                    ...actionManagerServerData.actions,
                    ...serverData.actions,
                },
                menus: {
                    ...actionManagerServerData.menus,
                    ...serverData.menus,
                },
                models: {
                    ...actionManagerServerData.models,
                    ...serverData.models,
                },
                views: {
                    ...actionManagerServerData.views,
                    ...serverData.views,
                },
            };
            const webClient = await createWebClient({
                legacyParams,
                mockRPC,
                serverData: finalServerData,
            });
            registerCleanup(() => webClient.destroy());
            return webClient;
        });
    }
    const webClient = waitUntilEvent
        ? await afterEvent({ func: () => getWebClient(), ...waitUntilEvent, })
        : await getWebClient();
    const { env } = webClient;
    const { modelManager } = env.services.messaging;
    registerCleanup(async () => {
        const messaging = await env.services.messaging.get();
        messaging.delete();
    });
    if (waitUntilMessagingCondition === 'created') {
        await modelManager.messagingCreatedPromise;
    }
    if (waitUntilMessagingCondition === 'initialized') {
        await modelManager.messagingCreatedPromise;
        await modelManager.messagingInitializedPromise;
    }
    return {
        advanceTime: hasTimeControl ? getTimeControl() : undefined,
        afterEvent,
        env,
        get messaging() {
            return modelManager.messaging;
        },
        openDiscuss: getOpenDiscuss({ afterEvent, env }),
        async openResPartnerFormView({ partnerId } = {}, options = {}) {
            return afterNextRender(() =>
                env.services.action.doAction(
                    {
                        'name': 'Partner Form',
                        'res_model': 'res.partner',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[false, 'form']],
                    },
                    {
                        ...options,
                        props: {
                            resId: partnerId,
                            ...(options.props || {}),
                        },
                    },
                )
            );
        },
        webClient,
        get widget() {
            throw Error("don't use widget from start() result, use webClient instead");
        },
    };
}

//------------------------------------------------------------------------------
// Public: file utilities
//------------------------------------------------------------------------------

/**
 * Drag some files over a DOM element
 *
 * @param {DOM.Element} el
 * @param {Object[]} file must have been create beforehand
 *   @see testUtils.file.createFile
 */
function dragenterFiles(el, files) {
    const ev = new Event('dragenter', { bubbles: true });
    Object.defineProperty(ev, 'dataTransfer', {
        value: _createFakeDataTransfer(files),
    });
    el.dispatchEvent(ev);
}

/**
 * Drop some files on a DOM element
 *
 * @param {DOM.Element} el
 * @param {Object[]} files must have been created beforehand
 *   @see testUtils.file.createFile
 */
function dropFiles(el, files) {
    const ev = new Event('drop', { bubbles: true });
    Object.defineProperty(ev, 'dataTransfer', {
        value: _createFakeDataTransfer(files),
    });
    el.dispatchEvent(ev);
}

/**
 * Paste some files on a DOM element
 *
 * @param {DOM.Element} el
 * @param {Object[]} files must have been created beforehand
 *   @see testUtils.file.createFile
 */
function pasteFiles(el, files) {
    const ev = new Event('paste', { bubbles: true });
    Object.defineProperty(ev, 'clipboardData', {
        value: _createFakeDataTransfer(files),
    });
    el.dispatchEvent(ev);
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

export {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    dragenterFiles,
    dropFiles,
    nextAnimationFrame,
    nextTick,
    pasteFiles,
    start,
};
