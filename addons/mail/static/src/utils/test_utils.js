/** @odoo-module **/

import BusService from 'bus.BusService';

import { messagingService, messagingValues } from '@mail/services/messaging_service/messaging_service';
import { getMessagingComponent } from '@mail/utils/messaging_component';
import { nextTick } from '@mail/utils/utils';
import { MockModels } from '@mail/../tests/helpers/mock_models';

import AbstractStorageService from 'web.AbstractStorageService';
import { browser } from "@web/core/browser/browser";
import { registry } from '@web/core/registry';
import RamStorage from 'web.RamStorage';
import { makeTestPromise } from 'web.test_utils';
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

function beforeEach(self) {
    const data = MockModels.generateData();

    data.partnerRootId = 2;
    data['res.partner'].records.push({
        active: false,
        display_name: "OdooBot",
        id: data.partnerRootId,
    });

    data.currentPartnerId = 3;
    data['res.partner'].records.push({
        display_name: "Your Company, Mitchell Admin",
        id: data.currentPartnerId,
        name: "Mitchell Admin",
    });
    data.currentUserId = 2;
    data['res.users'].records.push({
        display_name: "Your Company, Mitchell Admin",
        id: data.currentUserId,
        name: "Mitchell Admin",
        partner_id: data.currentPartnerId,
    });

    data.publicPartnerId = 4;
    data['res.partner'].records.push({
        active: false,
        display_name: "Public user",
        id: data.publicPartnerId,
    });
    data.publicUserId = 3;
    data['res.users'].records.push({
        active: false,
        display_name: "Public user",
        id: data.publicUserId,
        name: "Public user",
        partner_id: data.publicPartnerId,
    });

    const originals = {
        '_.debounce': _.debounce,
        '_.throttle': _.throttle,
    };

    (function patch() {
        // patch _.debounce and _.throttle to be fast and synchronous
        _.debounce = _.identity;
        _.throttle = _.identity;
    })();

    function unpatch() {
        _.debounce = originals['_.debounce'];
        _.throttle = originals['_.throttle'];
    }

    Object.assign(self, {
        components: [],
        data,
        unpatch,
        widget: undefined
    });

    Object.defineProperty(self, 'messaging', {
        get() {
            if (!this.env || !this.env.services.messaging) {
                return undefined;
            }
            return this.env.services.messaging.messaging;
        },
    });
}

function afterEach(self) {
    // The components must be destroyed before the widget, because the
    // widget might destroy the models before destroying the components,
    // and the components might still rely on messaging (or other) record(s).
    while (self.components.length > 0) {
        const component = self.components.pop();
        component.destroy();
    }
    if (self.widget) {
        self.widget.destroy();
        self.widget = undefined;
    }
    if (self.messaging) {
        self.messaging.delete();
    }
    self.env = undefined;
    self.unpatch();
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
    const Component = getMessagingComponent(componentName);
    Component.env = self.env;
    const component = new Component(null, props);
    delete Component.env;
    self.components.push(component);
    await afterNextRender(() => component.mount(target));
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

/**
 * Main function used to make a mocked environment with mocked messaging env.
 *
 * @param {Object} [param0={}]
 * @param {string} [param0.arch] makes only sense when `param0.hasView` is set:
 *   the arch to use in createView.
 * @param {Object} [param0.archs]
 * @param {boolean} [param0.autoOpenDiscuss=false] makes only sense when
 *   `param0.hasDiscuss` is set: determine whether mounted discuss should be
 *   open initially.
 * @param {boolean} [param0.debug=false]
 * @param {Object} [param0.data] makes only sense when `param0.hasView` is set:
 *   the data to use in createView.
 * @param {Object} [param0.discuss={}] makes only sense when `param0.hasDiscuss`
 *   is set: provide data that is passed to discuss widget (= client action) as
 *   2nd positional argument.
 * @param {Object} [param0.env={}]
 * @param {function} [param0.mockFetch]
 * @param {function} [param0.mockRPC]
 * @param {boolean} [param0.hasDiscuss=false] if set, mount discuss app.
 * @param {boolean} [param0.hasTimeControl=false] if set, all flow of time
 *   with `env.browser.setTimeout` are fully controlled by test itself.
 *     @see addTimeControlToEnv that adds `advanceTime` function in
 *     `env.testUtils`.
 * @param {boolean} [param0.hasView=false] if set, use createView to create a
 *   view instead of a generic widget.
 * @param {integer} [param0.loadingBaseDelayDuration=0]
 * @param {Deferred|Promise} [param0.messagingBeforeCreationDeferred=Promise.resolve()]
 *   Deferred that let tests block messaging creation and simulate resolution.
 *   Useful for testing working components when messaging is not yet created.
 * @param {string} [param0.model] makes only sense when `param0.hasView` is set:
 *   the model to use in createView.
 * @param {integer} [param0.res_id] makes only sense when `param0.hasView` is set:
 *   the res_id to use in createView.
 * @param {Object} [param0.services]
 * @param {Object} [param0.session]
 * @param {Object} [param0.View] makes only sense when `param0.hasView` is set:
 *   the View class to use in createView.
 * @param {Object} [param0.viewOptions] makes only sense when `param0.hasView`
 *   is set: the view options to use in createView.
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
 * @param {...Object} [param0.kwargs]
 * @throws {Error} in case some provided parameters are wrong, such as
 *   `waitUntilMessagingCondition`.
 * @returns {Object}
 */
async function start(param0 = {}) {
    const {
        browser: browserValues = {},
        env: providedEnv,
        hasDiscuss = false,
        hasTimeControl = false,
        loadingBaseDelayDuration = 0,
        messagingBeforeCreationDeferred = Promise.resolve(),
        mockRPC,
        services,
        waitUntilEvent,
        waitUntilMessagingCondition = 'initialized',
    } = param0;
    if (!['none', 'created', 'initialized'].includes(waitUntilMessagingCondition)) {
        throw Error(`Unknown parameter value ${waitUntilMessagingCondition} for 'waitUntilMessaging'.`);
    }
    delete param0.browser;
    delete param0.env;
    delete param0.mockRPC;
    delete param0.hasDiscuss;
    delete param0.hasTimeControl;
    delete param0.hasView;
    delete param0.services;
    if (hasDiscuss) {
        // add the action and open it correctly, I guess from the web client actions
    }
    const messagingBus = new EventBus();
    let env = Object.assign(providedEnv || {});
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
    registry.category('services').add('messaging', messagingService);
    registry.category('systray').add('mail.messaging_menu', {
        Component: getMessagingComponent('MessagingMenu'),
        props: {},
    }, { sequence: 5 });
    const kwargs = Object.assign({}, param0, {
        archs: Object.assign({}, {
            'mail.activity,false,form': '<form/>',
            'mail.compose.message,false,form': '<form/>',
            'mail.message,false,search': '<search/>',
            'mail.wizard.invite,false,form': '<form/>',
            'res.partner,false,form': '<form/>',
            'res.partner,false,kanban': '<kanban><templates/></kanban>',
            'res.partner,false,list': '<list/>',
            'res.partner,false,search': '<search/>',
        }, param0.archs),
        debug: param0.debug || false,
    }, { env });
    let serverData;
    if (!kwargs.serverData) {
        serverData = getActionManagerServerData();
    } else {
        serverData = kwargs.serverData;
        delete kwargs.serverData;
    }

    if (kwargs.actions) {
        const actions = {};
        kwargs.actions.forEach((act) => {
            actions[act.xml_id || act.id] = act;
        });
        Object.assign(serverData.actions, actions);
        delete kwargs.actions;
    }

    Object.assign(serverData.views, kwargs.archs);
    delete kwargs.archs;

    if (kwargs.data && kwargs.data.currentPartnerId) {
        serverData.currentPartnerId = kwargs.data.currentPartnerId;
        delete kwargs.data.currentPartnerId;
    }
    if (kwargs.data && kwargs.data.currentUserId) {
        serverData.currentUserId = kwargs.data.currentUserId;
        delete kwargs.data.currentUserId;
    }
    if (kwargs.data && kwargs.data.partnerRootId) {
        serverData.partnerRootId = kwargs.data.partnerRootId;
        delete kwargs.data.partnerRootId;
    }
    if (kwargs.data && kwargs.data.publicPartnerId) {
        serverData.publicPartnerId = kwargs.data.publicPartnerId;
        delete kwargs.data.publicPartnerId;
    }
    if (kwargs.data && kwargs.data.publicUserId) {
        serverData.publicUserId = kwargs.data.publicUserId;
        delete kwargs.data.publicUserId;
    }
    Object.assign(serverData.models, kwargs.data);
    delete kwargs.data;

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
    const legacyParams = {
        ...kwargs,
        env,
        serviceRegistry: legacyServiceRegistry,
        withLegacyMockServer: true,
    };
    const afterEvent = getAfterEvent(messagingBus);
    async function getWebClient() {
        return afterNextRender(() => createWebClient({ serverData, mockRPC, legacyParams }));
    }
    const webClientComponent = waitUntilEvent
        ? await afterEvent({ func: () => getWebClient(), ...waitUntilEvent, })
        : await getWebClient();
    const { modelManager } = webClientComponent.env.services.messaging;
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
        env: webClientComponent.env,
        widget: webClientComponent,
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
