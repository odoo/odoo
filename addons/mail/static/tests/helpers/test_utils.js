/** @odoo-module **/

import BusService from 'bus.BusService';

import { MessagingMenuContainer } from '@mail/components/messaging_menu_container/messaging_menu_container';
import {
    addMessagingToEnv,
    addTimeControlToEnv,
} from '@mail/env/test_env';
import { insertAndReplace, replace } from '@mail/model/model_field_command';
import { ChatWindowService } from '@mail/services/chat_window_service/chat_window_service';
import { MessagingService } from '@mail/services/messaging/messaging';
import { makeDeferred } from '@mail/utils/deferred';
import { DialogService } from '@mail/services/dialog_service/dialog_service';
import { getMessagingComponent } from '@mail/utils/messaging_component';
import { nextTick } from '@mail/utils/utils';
import { DiscussWidget } from '@mail/widgets/discuss/discuss';

import core from 'web.core';
import AbstractStorageService from 'web.AbstractStorageService';
import RamStorage from 'web.RamStorage';
import {
    createView,
    mock,
} from 'web.test_utils';
import Widget from 'web.Widget';
import { registry } from '@web/core/registry';
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient, getActionManagerServerData } from "@web/../tests/webclient/helpers";

import LegacyRegistry from "web.Registry";
import MockServer from 'web.MockServer';

const { App, Component, EventBus } = owl;
const { afterNextRender } = App;
const {
    addMockEnvironment,
    patch: legacyPatch,
    unpatch: legacyUnpatch,
} = mock;

const modelDefinitionsPromise = new Promise(resolve => {
    QUnit.begin(() => resolve(getModelDefinitions()));
});

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
 * @param {Object) params
 * @param {function) params.afterNextRender
 * @returns {Object} update callbacks
 */
function _useChatWindow(callbacks, { afterNextRender }) {
    const {
        mount: prevMount,
        destroy: prevDestroy,
    } = callbacks;
    return Object.assign({}, callbacks, {
        mount: prevMount.concat(async () => {
            // trigger mounting of chat window manager
            await afterNextRender(() => Component.env.services['chat_window']._onWebClientReady());
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
 * @param {Object) params
 * @param {function) params.afterNextRender
 * @returns {Object} update callbacks
 */
function _useDialog(callbacks, { afterNextRender }) {
    const {
        mount: prevMount,
        destroy: prevDestroy,
    } = callbacks;
    return Object.assign({}, callbacks, {
        mount: prevMount.concat(async () => {
            // trigger mounting of dialog manager
            await afterNextRender(() => Component.env.services['dialog']._onWebClientReady());
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
 * @param {Object) params
 * @param {function) params.afterNextRender
 * @return {Object} update callbacks
 */
function _useDiscuss(callbacks, { afterNextRender }) {
    const {
        init: prevInit,
        mount: prevMount,
        return: prevReturn,
    } = callbacks;
    let discussWidget;
    const state = {
        discussData: {},
    };
    return Object.assign({}, callbacks, {
        init: prevInit.concat(params => {
            const {
                discuss: discussData = state.discussData
            } = params;
            Object.assign(state, { discussData });
            delete params.discuss;
        }),
        mount: prevMount.concat(async params => {
            const { selector, widget } = params;
            DiscussWidget.prototype._pushStateActionManager = () => {};
            discussWidget = new DiscussWidget(widget, state.discussData);
            await discussWidget.appendTo($(selector));
        }),
        return: prevReturn.concat(result => {
            Object.assign(result, { discussWidget });
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
    return new Promise(function (resolve) {
        setTimeout(() => requestAnimationFrame(() => resolve()));
    });
}

//------------------------------------------------------------------------------
// Model definitions setup
//------------------------------------------------------------------------------

export const TEST_USER_IDS = {
    partnerRootId: 2,
    currentPartnerId: 3,
    currentUserId: 2,
    publicPartnerId: 4,
    publicUserId: 3,
};

/**
 * Fetch model definitions from the server then insert fields present in the
 * `mail.model.definitions` registry. Use `addModelNamesToFetch`/`insertModelFields`
 * helpers in order to add models to be fetched, default values to the fields,
 * fields to a model definition.
 *
 * @return {Map<string, Object>} A map from model names to model fields definitions.
 * @see model_definitions_setup.js
 */
async function getModelDefinitions() {
    const modelDefinitionsRegistry = registry.category('mail.model.definitions');
    const modelNamesToFetch = modelDefinitionsRegistry.get('modelNamesToFetch');
    const fieldsToInsertRegistry = modelDefinitionsRegistry.category('fieldsToInsert');

    // fetch the model definitions.
    const formData = new FormData();
    formData.append('csrf_token', core.csrf_token);
    formData.append('model_names_to_fetch', JSON.stringify(modelNamesToFetch));
    const response = await window.fetch('/mail/get_model_definitions', { body: formData, method: 'POST' });
    if (response.status !== 200) {
        throw new Error('Error while fetching required models');
    }
    const modelDefinitions = new Map(Object.entries(await response.json()));

    for (const [modelName, fields] of modelDefinitions) {
         // insert fields present in the fieldsToInsert registry : if the field
         // exists, update its default value according to the one in the
         // registry; If it does not exist, add it to the model definition.
        const fieldNamesToFieldToInsert = fieldsToInsertRegistry.category(modelName).getEntries();
        for (const [fname, fieldToInsert] of fieldNamesToFieldToInsert) {
            if (fname in fields) {
                fields[fname].default = fieldToInsert.default;
            } else {
                fields[fname] = fieldToInsert;
            }
        }
        // apply default values for date like fields if none was passed.
        for (const fname in fields) {
            const field = fields[fname];
            if (['date', 'datetime'].includes(field.type) && !field.default) {
                const defaultFieldValue = field.type === 'date'
                    ? () => moment.utc().format('YYYY-MM-DD')
                    : () => moment.utc().format("YYYY-MM-DD HH:mm:ss");
                field.default = defaultFieldValue;
            } else if (fname === 'active' && !('default' in field)) {
                // records are active by default.
                field.default = true;
            }
        }
    }
    // add models present in the fake models registry to the model definitions.
    const fakeModels = modelDefinitionsRegistry.category('fakeModels').getEntries();
    for (const [modelName, fields] of fakeModels) {
        modelDefinitions.set(modelName, fields);
    }
    return modelDefinitions;
}

let pyEnv;
/**
 * Creates an environment that can be used to setup test data as well as
 * creating data after test start.
 *
 * @returns {Object} An environment that can be used to interact with the mock
 * server (creation, deletion, update of records...)
 */
 export async function startServer() {
    const data = { ...TEST_USER_IDS };
    const modelDefinitions = await modelDefinitionsPromise;
    const recordsToInsertRegistry = registry.category('mail.model.definitions').category('recordsToInsert');
    for (const [modelName, fields] of modelDefinitions) {
        const records = [];
        if (recordsToInsertRegistry.contains(modelName)) {
            // prevent tests from mutating the records.
            records.push(...JSON.parse(JSON.stringify(recordsToInsertRegistry.get(modelName))));
        }
        data[modelName] = { fields: { ...fields }, records };
    }
    pyEnv = new Proxy(
        {
            mockServer: new MockServer(data, {}),
            ...TEST_USER_IDS,
        },
        {
            get(target, name) {
                if (target[name]) {
                    return target[name];
                }
                return {
                    /**
                     * Simulate a 'create' operation on a model.
                     *
                     * @param {Object[]|Object} values records to be created.
                     * @returns {integer[]|integer} array of ids if more than one value was passed,
                     * id of created record otherwise.
                     */
                    create(values = {}) {
                        if (!Array.isArray(values)) {
                            values = [values];
                        }
                        const recordIds = values.map(value => target.mockServer._mockCreate(name, value))
                        return recordIds.length === 1 ? recordIds[0] : recordIds;
                    },
                    /**
                     * Simulate a 'search' operation on a model.
                     *
                     * @param {Array} domain
                     * @param {Object} context
                     * @returns {integer[]} array of ids corresponding to the given domain.
                     */
                    search(domain, context = {}) {
                        return target.mockServer._mockSearch(name, [domain], context);
                    },
                    /**
                     * Simulate a 'search_read' operation on a model.
                     *
                     * @param {Array} domain
                     * @param {Object} context
                     * @returns {Object[]} array of records corresponding to the given domain.
                     */
                    searchRead(domain, context = {}) {
                        return target.mockServer._mockSearchRead(name, [], { domain, context });
                    },
                    /**
                     * Simulate an 'unlink' operation on a model.
                     *
                     * @param {integer[]} ids
                     * @returns {boolean} mockServer 'unlink' method always returns true.
                     */
                    unlink(ids) {
                        return target.mockServer._mockUnlink(name, [ids]);
                    },
                    /**
                     * Simulate a 'write' operation on a model.
                     *
                     * @param {integer[]} ids ids of records to write on.
                     * @param {Object} values values to write on the records matching given ids.
                     * @returns {boolean} mockServer 'write' method always returns true.
                     */
                    write(ids, values) {
                        return target.mockServer._mockWrite(name, [ids, values]);
                    },
                };
            },
            set(target, name, value) {
                return target[name] = value;
            },
         },
    );
    registerCleanup(() => pyEnv = undefined);
    return pyEnv;
}

//------------------------------------------------------------------------------
// Public: test lifecycle
//------------------------------------------------------------------------------

function getAfterEvent({ messagingBus }) {
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
        // If the event is triggered before the end of the async function,
        // ensure the function finishes its job before returning.
        await funcRes;
    };
}

/**
 * Creates a new root Component, with the given props, and mounts it on target.
 * Assumes that self.env is set to the correct value.
 * Components created this way are automatically registered for clean up after
 * the test.
 *
 * @param {Object} env the current environment
 * @param {Object} Component the class of the component to create
 * @param {Object} param2
 * @param {Object} [param2.props={}] forwarded to component constructor
 * @param {DOM.Element} param2.target mount target for the component
 * @returns {Component}
 */
async function createRootComponent(env, Component, { props = {}, target }) {
    const app = new App(Component, {
        props,
        templates: window.__OWL_TEMPLATES__,
        env,
        test: true,
    });
    // The components must be destroyed before the widget, because the
    // widget might destroy the models before destroying the components,
    // and the components might still rely on messaging (or other) record(s).
    registerCleanup(() => app.destroy());
    let component;
    await afterNextRender(() => {
        component = app.mount(target);
    });
    return component;
}

/**
 * Creates and returns a new root messaging component, based on the given
 * componentName and with the given props, and mounts it on target.
 * Assumes that self.env is set to the correct value.
 * Components created this way are automatically registered for clean up after
 * the test.
 *
 * @param {Object} env the current environment
 * @param {string} componentName the class name of the component to create
 * @param {Object} param2
 * @param {Object} [param2.props={}] forwarded to component constructor
 * @param {DOM.Element} param2.target mount target for the component
 * @returns {Component}
 */
async function createRootMessagingComponent(env, componentName, { props = {}, target }) {
    return await createRootComponent(env, getMessagingComponent(componentName), { props, target });
}

function getClick({ afterNextRender }) {
    return async function click(selector) {
        await afterNextRender(() => document.querySelector(selector).click());
    };
}

function getCreateChatterContainerComponent({ afterEvent, env, widget }) {
    return async function createChatterContainerComponent(props, { waitUntilMessagesLoaded = true } = {}) {
        let chatterContainerComponent;
        async function func() {
            chatterContainerComponent = await createRootMessagingComponent(env, "ChatterContainer", {
                props,
                target: widget.el,
            });
        }
        if (waitUntilMessagesLoaded) {
            await afterNextRender(() => afterEvent({
                eventName: 'o-thread-view-hint-processed',
                func,
                message: "should wait until chatter loaded messages after creating chatter container component",
                predicate: ({ hint, threadViewer }) => {
                    return (
                        hint.type === 'messages-loaded' &&
                        threadViewer &&
                        threadViewer.chatter &&
                        threadViewer.chatter.threadModel === props.threadModel &&
                        threadViewer.chatter.threadId === props.threadId
                    );
                },
            }));
        } else {
            await func();
        }
        return chatterContainerComponent;
    };
}

function getCreateComposerComponent({ env, modelManager, widget }) {
    return async function createComposerComponent(composer, props) {
        const composerView = modelManager.messaging.models['ComposerView'].create({
            qunitTest: insertAndReplace({
                composer: replace(composer),
            }),
        });
        return await createRootMessagingComponent(env, "Composer", {
            props: { localId: composerView.localId, ...props },
            target: widget.el,
        });
    };
}

function getCreateComposerSuggestionComponent({ env, modelManager, widget }) {
    return async function createComposerSuggestionComponent(composer, props) {
        const composerView = modelManager.messaging.models['ComposerView'].create({
            qunitTest: insertAndReplace({
                composer: replace(composer),
            }),
        });
        await createRootMessagingComponent(env, "ComposerSuggestion", {
            props: { ...props, composerViewLocalId: composerView.localId },
            target: widget.el,
        });
    };
}

function getCreateMessageComponent({ env, modelManager, widget }) {
    return async function createMessageComponent(message) {
        const messageView = modelManager.messaging.models['MessageView'].create({
            message: replace(message),
            qunitTest: insertAndReplace(),
        });
        await createRootMessagingComponent(env, "Message", {
            props: { localId: messageView.localId },
            target: widget.el,
        });
    };
}

function getCreateMessagingMenuComponent({ env, widget }) {
    return async function createMessagingMenuComponent() {
        return await createRootComponent({ env }, MessagingMenuContainer, { target: widget.el });
    };
}

function getCreateNotificationListComponent({ env, modelManager, widget }) {
    return async function createNotificationListComponent({ filter = 'all' } = {}) {
        const notificationListView = modelManager.messaging.models['NotificationListView'].create({
            filter,
            qunitTestOwner: insertAndReplace(),
        });
        await createRootMessagingComponent(env, "NotificationList", {
            props: { localId: notificationListView.localId },
            target: widget.el,
        });
    };
}

function getCreateThreadViewComponent({ afterEvent, env, widget }) {
    return async function createThreadViewComponent(threadView, otherProps = {}, { isFixedSize = false, waitUntilMessagesLoaded = true } = {}) {
        let target;
        if (isFixedSize) {
            // needed to allow scrolling in some tests
            const div = document.createElement('div');
            Object.assign(div.style, {
                display: 'flex',
                'flex-flow': 'column',
                height: '300px',
            });
            widget.el.append(div);
            target = div;
        } else {
            target = widget.el;
        }
        async function func() {
            return createRootMessagingComponent(env, "ThreadView", { props: { localId: threadView.localId, ...otherProps }, target });
        }
        if (waitUntilMessagesLoaded) {
            await afterNextRender(() => afterEvent({
                eventName: 'o-thread-view-hint-processed',
                func,
                message: "should wait until thread loaded messages after creating thread view component",
                predicate: ({ hint, threadViewer }) => {
                    return (
                        hint.type === 'messages-loaded' &&
                        threadViewer.threadView === threadView
                    );
                },
            }));
        } else {
            await func();
        }
    };
}

function getOpenDiscuss({ afterNextRender, discussWidget }) {
    return async function openDiscuss() {
        await afterNextRender(() => discussWidget.on_attach_callback());
        // Some changes in the models are made on mount, but these changes don't
        // cause a rerender directly, they cause the model to fetch more data
        // but we cannot wait for that data to come back as the model manager
        // doesn't expose it. This means that in the following microticks, the
        // data will come back from the server and cause a render. The following
        // is a way for us to catch the render cascade caused by the data coming
        // back and wait for it.
        await afterNextRender(() => {
            discussWidget.app.root.render();
        });
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
 *   open initially. Deprecated, call openDiscuss() instead.
 * @param {boolean} [param0.debug=false]
 * @param {Object} [param0.data] makes only sense when `param0.hasView` is set:
 *   the data to use in createView.
 * @param {Object} [param0.discuss={}] makes only sense when `param0.hasDiscuss`
 *   is set: provide data that is passed to discuss widget (= client action) as
 *   2nd positional argument.
 * @param {Object} [param0.env={}]
 * @param {function} [param0.mockFetch]
 * @param {function} [param0.mockRPC]
 * @param {boolean} [param0.hasWebClient=false] if set, use
 *   createWebClient
 * @param {boolean} [param0.hasChatWindow=false] if set, mount chat window
 *   service.
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
 * @param {Element} [param0.target] if provided, the component will be mounted inside
 *   that element (only used if `params0.hasWebClient` is true)
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
    // patch _.debounce and _.throttle to be fast and synchronous.
    patchWithCleanup(_, {
        debounce: func => func,
        throttle: func => func,
    });
    let callbacks = {
        init: [],
        mount: [],
        destroy: [],
        return: [],
    };
    const {
        autoOpenDiscuss = false,
        env: providedEnv,
        hasWebClient = false,
        hasChatWindow = false,
        hasDialog = false,
        hasDiscuss = false,
        hasTimeControl = false,
        hasView = false,
        loadingBaseDelayDuration = 0,
        messagingBeforeCreationDeferred = Promise.resolve(),
        target = getFixture(),
        waitUntilEvent,
        waitUntilMessagingCondition = 'initialized',
    } = param0;
    if (!['none', 'created', 'initialized'].includes(waitUntilMessagingCondition)) {
        throw Error(`Unknown parameter value ${waitUntilMessagingCondition} for 'waitUntilMessaging'.`);
    }
    delete param0.autoOpenDiscuss;
    delete param0.env;
    delete param0.hasWebClient;
    delete param0.hasChatWindow;
    delete param0.hasDiscuss;
    delete param0.hasTimeControl;
    delete param0.hasView;
    delete param0.target;
    if (hasChatWindow) {
        callbacks = _useChatWindow(callbacks, { afterNextRender });
    }
    if (hasDialog) {
        callbacks = _useDialog(callbacks, { afterNextRender });
    }
    if (hasDiscuss) {
        callbacks = _useDiscuss(callbacks, { afterNextRender });
    }
    const messagingBus = new EventBus();
    const {
        init: initCallbacks,
        mount: mountCallbacks,
        destroy: destroyCallbacks,
        return: returnCallbacks,
    } = callbacks;
    const { debug = false } = param0;
    initCallbacks.forEach(callback => callback(param0));
    const testSetupDoneDeferred = makeDeferred();
    let env = Object.assign(providedEnv || {});
    env.session = Object.assign(
        {
            is_bound: Promise.resolve(),
            url: s => s,
        },
        env.session
    );
    env.isDebug = env.isDebug || (() => true);
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
        messaging: MessagingService.extend({
            // test specific values
            messagingValues: {
                autofetchPartnerImStatus: false,
                disableAnimation: true,
                loadingBaseDelayDuration,
                messagingBus,
            },
            /**
             * Override to ensure tests run in debug mode to catch all potential
             * programming errors and provide better message when they happen.
             */
            init(...args) {
                this._super(...args);
                this.modelManager.isDebug = true;
            },
            /**
             * Override:
             * - to ensure the test setup is complete before starting otherwise
             *   for example the mock server might not be ready yet at init
             *   messaging,
             * - to add control on when messaging is created, useful to test
             *   spinners and race conditions.
             *
             * @override
             */
            async start() {
                const _super = this._super.bind(this);
                await testSetupDoneDeferred;
                await messagingBeforeCreationDeferred;
                _super();
            },
        }),
    }, param0.services);

    if (!param0.data && (!param0.serverData || !param0.serverData.models)) {
        pyEnv = pyEnv || await startServer();
        const data = pyEnv.mockServer.data;
        Object.assign(data, TEST_USER_IDS);
        if (hasWebClient) {
            param0.serverData = param0.serverData || getActionManagerServerData();
            param0.serverData.models = data;
        } else {
            param0.data = data;
        }
    }

    const kwargs = Object.assign({}, param0, {
        archs: Object.assign({}, {
            'mail.message,false,search': '<search/>'
        }, param0.archs),
        debug: param0.debug || false,
        services: Object.assign({}, services, param0.services),
    }, { env });
    let widget;
    let mockServer;
    let testEnv;
    const selector = debug ? 'body' : '#qunit-fixture';
    if (hasView) {
        widget = await createView(kwargs);
        legacyPatch(widget, {
            destroy() {
                destroyCallbacks.forEach(callback => callback({ widget }));
                this._super(...arguments);
                legacyUnpatch(widget);
            }
        });
    } else if (hasWebClient) {
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

        Object.assign(serverData.models, kwargs.data);
        delete kwargs.data;

        const mockRPC = kwargs.mockRPC;
        delete kwargs.mockRPC;

        if (kwargs.services) {
            const serviceRegistry = kwargs.serviceRegistry = new LegacyRegistry();
            for (const sname in kwargs.services) {
                serviceRegistry.add(sname, kwargs.services[sname]);
            }
            delete kwargs.services;
        }

        const legacyParams = kwargs;
        legacyParams.withLegacyMockServer = true;
        legacyParams.env = env;

        widget = await createWebClient({ target, serverData, mockRPC, legacyParams });

        legacyPatch(widget, {
            destroy() {
                destroyCallbacks.forEach(callback => callback({ widget }));
                legacyUnpatch(widget);
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
            },
        });
    }
    // get the final test env after execution of createView/createWebClient/addMockEnvironment
    testEnv = Component.env;
    // link the pyEnv to the actual mockServer after execution of createView/createWebClient/addMockEnvironment
    if (pyEnv) {
        pyEnv.mockServer = MockServer.currentMockServer;
        mockServer = pyEnv.mockServer;
    }
    const afterEvent = getAfterEvent({ messagingBus });
    let waitUntilEventPromise;
    if (waitUntilEvent) {
        waitUntilEventPromise = afterEvent({ func: () => testSetupDoneDeferred.resolve(), ...waitUntilEvent, });
    } else {
        testSetupDoneDeferred.resolve();
        waitUntilEventPromise = Promise.resolve();
    }
    const result = {
        afterEvent,
        env: testEnv,
        mockServer,
        pyEnv,
        widget,
    };
    const { modelManager } = testEnv.services.messaging;
    registerCleanup(async() => {
        widget.destroy();
        await modelManager.messagingInitializedPromise;
        modelManager.messaging.delete();
    });
    if (waitUntilMessagingCondition === 'created') {
        await modelManager.messagingCreatedPromise;
    }
    if (waitUntilMessagingCondition === 'initialized') {
        await modelManager.messagingCreatedPromise;
        await modelManager.messagingInitializedPromise;
    }
    if (mountCallbacks.length > 0) {
        await Promise.all(mountCallbacks.map(callback => callback({ selector, widget })));
    }
    returnCallbacks.forEach(callback => callback(result));
    const openDiscuss = getOpenDiscuss({ afterNextRender, discussWidget: result.discussWidget });
    if (autoOpenDiscuss) {
        await openDiscuss();
    }
    await waitUntilEventPromise;
    return {
        ...result,
        afterNextRender,
        click: getClick({ afterNextRender }),
        createChatterContainerComponent: getCreateChatterContainerComponent({ afterEvent, env: testEnv, widget }),
        createComposerComponent: getCreateComposerComponent({ env: testEnv, modelManager, widget }),
        createComposerSuggestionComponent: getCreateComposerSuggestionComponent({ env: testEnv, modelManager, widget }),
        createMessageComponent: getCreateMessageComponent({ env: testEnv, modelManager, widget }),
        createMessagingMenuComponent: getCreateMessagingMenuComponent({ env: testEnv, widget }),
        createNotificationListComponent: getCreateNotificationListComponent({ env: testEnv, modelManager, widget }),
        createThreadViewComponent: getCreateThreadViewComponent({ afterEvent, env: testEnv, widget }),
        insertText,
        messaging: modelManager.messaging,
        openDiscuss,
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
// Public: input utilities
//------------------------------------------------------------------------------

/**
 * @param {string} selector
 * @param {string} content
 */
 async function insertText(selector, content) {
    await afterNextRender(() => {
        document.querySelector(selector).focus();
        for (const char of content) {
            document.execCommand('insertText', false, char);
            document.querySelector(selector).dispatchEvent(new window.KeyboardEvent('keydown', { key: char }));
            document.querySelector(selector).dispatchEvent(new window.KeyboardEvent('keyup', { key: char }));
        }
    });
}

//------------------------------------------------------------------------------
// Public: DOM utilities
//------------------------------------------------------------------------------

/**
 * Determine if a DOM element has been totally scrolled
 *
 * A 1px margin of error is given to accomodate subpixel rounding issues and
 * Element.scrollHeight value being either int or decimal
 *
 * @param {DOM.Element} el
 * @returns {boolean}
 */
function isScrolledToBottom(el) {
    return Math.abs(el.scrollHeight - el.clientHeight - el.scrollTop) <= 1;
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

export {
    afterNextRender,
    createRootMessagingComponent,
    dragenterFiles,
    dropFiles,
    isScrolledToBottom,
    nextAnimationFrame,
    nextTick,
    pasteFiles,
    start,
};
