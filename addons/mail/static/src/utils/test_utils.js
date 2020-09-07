odoo.define('mail/static/src/utils/test_utils.js', function (require) {
'use strict';

const BusService = require('bus.BusService');

const {
    addMessagingToEnv,
    addTimeControlToEnv,
} = require('mail/static/src/env/test_env.js');
const ModelManager = require('mail/static/src/model/model_manager.js');
const ChatWindowService = require('mail/static/src/services/chat_window_service/chat_window_service.js');
const DialogService = require('mail/static/src/services/dialog_service/dialog_service.js');
const { nextTick } = require('mail/static/src/utils/utils.js');
const DiscussWidget = require('mail/static/src/widgets/discuss/discuss.js');
const MessagingMenuWidget = require('mail/static/src/widgets/messaging_menu/messaging_menu.js');
const MockModels = require('mail/static/tests/helpers/mock_models.js');

const AbstractStorageService = require('web.AbstractStorageService');
const NotificationService = require('web.NotificationService');
const RamStorage = require('web.RamStorage');
const {
    createActionManager,
    createView,
    makeTestPromise,
    mock: {
        addMockEnvironment,
        patch: legacyPatch,
        unpatch: legacyUnpatch,
    },
} = require('web.test_utils');
const Widget = require('web.Widget');

const { Component } = owl;

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

/**
 * @private
 * @param {Object} callbacks
 * @param {function[]} callbacks.init
 * @param {function[]} callbacks.mount
 * @param {function[]} callbacks.destroy
 * @param {function[]} callbacks.return
 * @returns {Object} update callbacks
 */
function _useChatWindow(callbacks) {
    const {
        mount: prevMount,
        destroy: prevDestroy,
    } = callbacks;
    return Object.assign({}, callbacks, {
        mount: prevMount.concat(async () => {
            // trigger mounting of chat window manager
            await Component.env.services['chat_window']._onWebClientReady();
        }),
        destroy: prevDestroy.concat(() => {
            Component.env.services['chat_window'].destroy();
        }),
    });
}

/**
 * @private
 * @param {Object} callbacks
 * @param {function[]} callbacks.init
 * @param {function[]} callbacks.mount
 * @param {function[]} callbacks.destroy
 * @param {function[]} callbacks.return
 * @returns {Object} update callbacks
 */
function _useDialog(callbacks) {
    const {
        mount: prevMount,
        destroy: prevDestroy,
    } = callbacks;
    return Object.assign({}, callbacks, {
        mount: prevMount.concat(async () => {
            // trigger mounting of dialog manager
            await Component.env.services['dialog']._onWebClientReady();
        }),
        destroy: prevDestroy.concat(() => {
            Component.env.services['dialog'].destroy();
        }),
    });
}

/**
 * @private
 * @param {Object} callbacks
 * @param {function[]} callbacks.init
 * @param {function[]} callbacks.mount
 * @param {function[]} callbacks.destroy
 * @param {function[]} callbacks.return
 * @return {Object} update callbacks
 */
function _useDiscuss(callbacks) {
    const {
        init: prevInit,
        mount: prevMount,
        return: prevReturn,
    } = callbacks;
    let discussWidget;
    const state = {
        autoOpenDiscuss: false,
        discussData: {},
    };
    return Object.assign({}, callbacks, {
        init: prevInit.concat(params => {
            const {
                autoOpenDiscuss = state.autoOpenDiscuss,
                discuss: discussData = state.discussData
            } = params;
            Object.assign(state, { autoOpenDiscuss, discussData });
            delete params.autoOpenDiscuss;
            delete params.discuss;
        }),
        mount: prevMount.concat(async params => {
            const { selector, widget } = params;
            DiscussWidget.prototype._pushStateActionManager = () => {};
            discussWidget = new DiscussWidget(widget, state.discussData);
            await discussWidget.appendTo($(selector));
            if (state.autoOpenDiscuss) {
                await discussWidget.on_attach_callback();
            }
        }),
        return: prevReturn.concat(result => {
            Object.assign(result, { discussWidget });
        }),
    });
}

/**
 * @private
 * @param {Object} callbacks
 * @param {function[]} callbacks.init
 * @param {function[]} callbacks.mount
 * @param {function[]} callbacks.destroy
 * @param {function[]} callbacks.return
 * @returns {Object} update callbacks
 */
function _useMessagingMenu(callbacks) {
    const {
        mount: prevMount,
        return: prevReturn,
    } = callbacks;
    let messagingMenuWidget;
    return Object.assign({}, callbacks, {
        mount: prevMount.concat(async ({ selector, widget }) => {
            messagingMenuWidget = new MessagingMenuWidget(widget, {});
            await messagingMenuWidget.appendTo($(selector));
            await messagingMenuWidget.on_attach_callback();
        }),
        return: prevReturn.concat(result => {
            Object.assign(result, { messagingMenuWidget });
        }),
    });
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
    }

    return afterNextRender;
})();


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
}

function afterEach(self) {
    if (self.env) {
        self.env.bus.off('hide_home_menu', null);
        self.env.bus.off('show_home_menu', null);
        self.env.bus.off('will_hide_home_menu', null);
        self.env.bus.off('will_show_home_menu', null);
    }
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
 * @param {Class} Component the component class to create
 * @param {Object} param2
 * @param {Object} [param2.props={}] forwarded to component constructor
 * @param {DOM.Element} param2.target mount target for the component
 * @returns {owl.Component} the new component instance
 */
async function createRootComponent(self, Component, { props = {}, target }) {
    Component.env = self.env;
    const component = new Component(null, props);
    delete Component.env;
    self.components.push(component);
    await afterNextRender(() => component.mount(target));
    return component;
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
 * @param {boolean} [param0.hasActionManager=false] if set, use
 *   createActionManager.
 * @param {boolean} [param0.hasChatWindow=false] if set, mount chat window
 *   service.
 * @param {boolean} [param0.hasDiscuss=false] if set, mount discuss app.
 * @param {boolean} [param0.hasMessagingMenu=false] if set, mount messaging
 *   menu.
 * @param {boolean} [param0.hasTimeControl=false] if set, all flow of time
 *   with `env.browser.setTimeout` are fully controlled by test itself.
 *     @see addTimeControlToEnv that adds `advanceTime` function in
 *     `env.testUtils`.
 * @param {boolean} [param0.hasView=false] if set, use createView to create a
 *   view instead of a generic widget.
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
    let callbacks = {
        init: [],
        mount: [],
        destroy: [],
        return: [],
    };
    const {
        env: providedEnv,
        hasActionManager = false,
        hasChatWindow = false,
        hasDialog = false,
        hasDiscuss = false,
        hasMessagingMenu = false,
        hasTimeControl = false,
        hasView = false,
        messagingBeforeCreationDeferred = Promise.resolve(),
        waitUntilEvent,
        waitUntilMessagingCondition = 'initialized',
    } = param0;
    if (!['none', 'created', 'initialized'].includes(waitUntilMessagingCondition)) {
        throw Error(`Unknown parameter value ${waitUntilMessagingCondition} for 'waitUntilMessaging'.`);
    }
    delete param0.env;
    delete param0.hasActionManager;
    delete param0.hasChatWindow;
    delete param0.hasDiscuss;
    delete param0.hasMessagingMenu;
    delete param0.hasTimeControl;
    delete param0.hasView;
    if (hasChatWindow) {
        callbacks = _useChatWindow(callbacks);
    }
    if (hasDialog) {
        callbacks = _useDialog(callbacks);
    }
    if (hasDiscuss) {
        callbacks = _useDiscuss(callbacks);
    }
    if (hasMessagingMenu) {
        callbacks = _useMessagingMenu(callbacks);
    }
    const {
        init: initCallbacks,
        mount: mountCallbacks,
        destroy: destroyCallbacks,
        return: returnCallbacks,
    } = callbacks;
    const { debug = false } = param0;
    initCallbacks.forEach(callback => callback(param0));

    let env = Object.assign(providedEnv || {});
    env.session = Object.assign(
        {
            is_bound: Promise.resolve(),
            url: s => s,
        },
        env.session
    );
    env = addMessagingToEnv(env);
    if (hasTimeControl) {
        env = addTimeControlToEnv(env);
    }

    const services = Object.assign({}, {
        bus_service: BusService.extend({
            _beep() {}, // Do nothing
            _poll() {}, // Do nothing
            _registerWindowUnload() {}, // Do nothing
            isOdooFocused() {
                return true;
            },
            updateOption() {},
        }),
        chat_window: ChatWindowService.extend({
            _getParentNode() {
                return document.querySelector(debug ? 'body' : '#qunit-fixture');
            },
            _listenHomeMenu: () => {},
        }),
        dialog: DialogService.extend({
            _getParentNode() {
                return document.querySelector(debug ? 'body' : '#qunit-fixture');
            },
            _listenHomeMenu: () => {},
        }),
        local_storage: AbstractStorageService.extend({ storage: new RamStorage() }),
        notification: NotificationService.extend(),
    }, param0.services);

    const kwargs = Object.assign({}, param0, {
        archs: Object.assign({}, {
            'mail.message,false,search': '<search/>'
        }, param0.archs),
        debug: param0.debug || false,
        services: Object.assign({}, services, param0.services),
    }, { env });
    let widget;
    let mockServer; // only in basic mode
    let testEnv;
    const selector = debug ? 'body' : '#qunit-fixture';
    if (hasView) {
        widget = await createView(kwargs);
        legacyPatch(widget, {
            destroy() {
                destroyCallbacks.forEach(callback => callback({ widget }));
                this._super(...arguments);
                legacyUnpatch(widget);
                if (testEnv) {
                    testEnv.destroyMessaging();
                }
            }
        });
    } else if (hasActionManager) {
        widget = await createActionManager(kwargs);
        legacyPatch(widget, {
            destroy() {
                destroyCallbacks.forEach(callback => callback({ widget }));
                this._super(...arguments);
                legacyUnpatch(widget);
                if (testEnv) {
                    testEnv.destroyMessaging();
                }
            }
        });
    } else {
        const Parent = Widget.extend({ do_push_state() {} });
        const parent = new Parent();
        mockServer = await addMockEnvironment(parent, kwargs);
        widget = new Widget(parent);
        await widget.appendTo($(selector));
        Object.assign(widget, {
            destroy() {
                delete widget.destroy;
                destroyCallbacks.forEach(callback => callback({ widget }));
                parent.destroy();
                if (testEnv) {
                    testEnv.destroyMessaging();
                }
            },
        });
    }

    testEnv = Component.env;

    /**
     * Components cannot use web.bus, because they cannot use
     * EventDispatcherMixin, and webclient cannot easily access env.
     * Communication between webclient and components by core.bus
     * (usable by webclient) and messagingBus (usable by components), which
     * the messaging service acts as mediator since it can easily use both
     * kinds of buses.
     */
    testEnv.bus.on(
        'hide_home_menu',
        null,
        () => testEnv.messagingBus.trigger('hide_home_menu')
    );
    testEnv.bus.on(
        'show_home_menu',
        null,
        () => testEnv.messagingBus.trigger('show_home_menu')
    );
    testEnv.bus.on(
        'will_hide_home_menu',
        null,
        () => testEnv.messagingBus.trigger('will_hide_home_menu')
    );
    testEnv.bus.on(
        'will_show_home_menu',
        null,
        () => testEnv.messagingBus.trigger('will_show_home_menu')
    );

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
    const afterEvent = (async ({ eventName, func, message, predicate, timeoutDelay = 5000 }) => {
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
            testEnv.messagingBus.on(eventName, null, data => {
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
        // If the event is triggered before the end of the async function,
        // ensure the function finishes its job before returning.
        await funcRes;
    });

    const result = {
        afterEvent,
        env: testEnv,
        mockServer,
        widget,
    };

    const start = async () => {
        messagingBeforeCreationDeferred.then(async () => {
            /**
             * Some models require session data, like locale text direction
             * (depends on fully loaded translation).
             */
            await env.session.is_bound;

            testEnv.modelManager = new ModelManager(testEnv);
            testEnv.modelManager.start();
            /**
             * Create the messaging singleton record.
             */
            testEnv.messaging = testEnv.models['mail.messaging'].create();
            testEnv.messaging.start().then(() =>
                testEnv.messagingInitializedDeferred.resolve()
            );
            testEnv.messagingCreatedPromise.resolve();
        });
        if (waitUntilMessagingCondition === 'created') {
            await testEnv.messagingCreatedPromise;
        }
        if (waitUntilMessagingCondition === 'initialized') {
            await testEnv.messagingInitializedDeferred;
        }

        if (mountCallbacks.length > 0) {
            await afterNextRender(async () => {
                await Promise.all(mountCallbacks.map(callback => callback({ selector, widget })));
            });
        }
        returnCallbacks.forEach(callback => callback(result));
    };
    if (waitUntilEvent) {
        await afterEvent(Object.assign({ func: start }, waitUntilEvent));
    } else {
        await start();
    }
    return result;
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

return {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    dragenterFiles,
    dropFiles,
    nextAnimationFrame,
    nextTick,
    pasteFiles,
    start,
};

});
