/** @odoo-module **/

import { MessagingMenuContainer } from '@mail/components/messaging_menu_container/messaging_menu_container';
import { insertAndReplace, replace } from '@mail/model/model_field_command';
import { getMessagingComponent } from '@mail/utils/messaging_component';
import { nextTick } from '@mail/utils/utils';
import { getAdvanceTime } from '@mail/../tests/helpers/time_control';
import { getWebClientReady } from '@mail/../tests/helpers/webclient_setup';

import { registry } from '@web/core/registry';
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { getFixture, makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";

import core from 'web.core';

const { App, EventBus } = owl;
const { afterNextRender } = App;
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
const VIEW_TYPE_TO_ARCH = {
    activity: '<activity><templates></templates></activity>',
    form: '<form/>',
    list: '<tree/>',
    search: '<search/>',
    kanban: '<kanban><templates></templates></kanban>',
};
/**
 * Creates an environment that can be used to setup test data as well as
 * creating data after test start.
 *
 * @returns {Object} An environment that can be used to interact with the mock
 * server (creation, deletion, update of records...)
 */
 export async function startServer() {
    const models = {};
    const views = {};
    const modelDefinitions = await modelDefinitionsPromise;
    const recordsToInsertRegistry = registry.category('mail.model.definitions').category('recordsToInsert');
    for (const [modelName, fields] of modelDefinitions) {
        const records = [];
        if (recordsToInsertRegistry.contains(modelName)) {
            // prevent tests from mutating the records.
            records.push(...JSON.parse(JSON.stringify(recordsToInsertRegistry.get(modelName))));
        }
        models[modelName] = { fields: { ...fields }, records };

        // generate default views for this model.
        for (const [viewType, viewArch] of Object.entries(VIEW_TYPE_TO_ARCH)) {
            views[`${modelName},false,${viewType}`] = viewArch;
        }
    }
    pyEnv = new Proxy(
        {
            getData() {
                return this.mockServer.models;
            },
            getViews() {
                return views;
            },
            ...TEST_USER_IDS,
            get currentPartner() {
                return this.mockServer.currentPartner;
            },
        },
        {
            get(target, name) {
                if (target[name]) {
                    return target[name];
                }
                const modelAPI = {
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
                        const recordIds = values.map(value => target.mockServer.mockCreate(name, value));
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
                        return target.mockServer.mockSearch(name, [domain], context);
                    },
                    /**
                     * Simulate a `search_count` operation on a model.
                     *
                     * @param {Array} domain
                     * @return {number} count of records matching the given domain.
                     */
                    searchCount(domain) {
                        return this.search(domain).length;
                    },
                    /**
                     * Simulate a 'search_read' operation on a model.
                     *
                     * @param {Array} domain
                     * @param {Object} kwargs
                     * @returns {Object[]} array of records corresponding to the given domain.
                     */
                    searchRead(domain, kwargs = {}) {
                        return target.mockServer.mockSearchRead(name, [domain], kwargs);
                    },
                    /**
                     * Simulate an 'unlink' operation on a model.
                     *
                     * @param {integer[]} ids
                     * @returns {boolean} mockServer 'unlink' method always returns true.
                     */
                    unlink(ids) {
                        return target.mockServer.mockUnlink(name, [ids]);
                    },
                    /**
                     * Simulate a 'write' operation on a model.
                     *
                     * @param {integer[]} ids ids of records to write on.
                     * @param {Object} values values to write on the records matching given ids.
                     * @returns {boolean} mockServer 'write' method always returns true.
                     */
                    write(ids, values) {
                        return target.mockServer.mockWrite(name, [ids, values]);
                    },
                };
                if (name === 'bus.bus') {
                    modelAPI['_sendone'] = target.mockServer._mockBusBus__sendone.bind(target.mockServer);
                    modelAPI['_sendmany'] = target.mockServer._mockBusBus__sendmany.bind(target.mockServer);
                }
                return modelAPI;
            },
            set(target, name, value) {
                return target[name] = value;
            },
         },
    );
    pyEnv['mockServer'] = new MockServer({ models }, {});
    await pyEnv['mockServer'].setup();
    registerCleanup(() => pyEnv = undefined);
    return pyEnv;
}

/**
 *
 * @returns {Object} An environment that can be used to interact with the mock
 * server (creation, deletion, update of records...)
 */
export function getPyEnv() {
    return pyEnv || startServer();
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
        return await funcRes;
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

function getCreateChatterContainerComponent({ afterEvent, env, target }) {
    return async function createChatterContainerComponent(props, { waitUntilMessagesLoaded = true } = {}) {
        let chatterContainerComponent;
        async function func() {
            chatterContainerComponent = await createRootMessagingComponent(env, "ChatterContainer", {
                props,
                target,
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

function getCreateComposerComponent({ env, modelManager, target }) {
    return async function createComposerComponent(composer, props) {
        const composerView = modelManager.messaging.models['ComposerView'].create({
            qunitTest: insertAndReplace({
                composer: replace(composer),
            }),
        });
        return await createRootMessagingComponent(env, "Composer", {
            props: { record: composerView, ...props },
            target,
        });
    };
}

function getCreateComposerSuggestionComponent({ env, modelManager, target }) {
    return async function createComposerSuggestionComponent(composer, props) {
        const composerView = modelManager.messaging.models['ComposerView'].create({
            qunitTest: insertAndReplace({
                composer: replace(composer),
            }),
        });
        await createRootMessagingComponent(env, "ComposerSuggestion", {
            props: { ...props, composerView: composerView },
            target,
        });
    };
}

function getCreateMessageComponent({ env, modelManager, target }) {
    return async function createMessageComponent(message) {
        const messageView = modelManager.messaging.models['MessageView'].create({
            message: replace(message),
            qunitTest: insertAndReplace(),
        });
        await createRootMessagingComponent(env, "Message", {
            props: { record: messageView },
            target,
        });
    };
}

function getCreateMessagingMenuComponent({ env, target }) {
    return async function createMessagingMenuComponent() {
        return await createRootComponent(env, MessagingMenuContainer, { target });
    };
}

function getCreateNotificationListComponent({ env, modelManager, target }) {
    return async function createNotificationListComponent({ filter = 'all' } = {}) {
        const notificationListView = modelManager.messaging.models['NotificationListView'].create({
            filter,
            qunitTestOwner: insertAndReplace(),
        });
        await createRootMessagingComponent(env, "NotificationList", {
            props: { record: notificationListView },
            target,
        });
    };
}

function getCreateThreadViewComponent({ afterEvent, env, target }) {
    return async function createThreadViewComponent(threadView, otherProps = {}, { isFixedSize = false, waitUntilMessagesLoaded = true } = {}) {
        let actualTarget;
        if (isFixedSize) {
            // needed to allow scrolling in some tests
            const div = document.createElement('div');
            Object.assign(div.style, {
                display: 'flex',
                'flex-flow': 'column',
                height: '300px',
            });
            target.appendChild(div);
            actualTarget = div;
        } else {
            actualTarget = target;
        }
        async function func() {
            return createRootMessagingComponent(env, "ThreadView", { props: { record: threadView, ...otherProps }, target: actualTarget });
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

function getOpenDiscuss(webClient, { context, params, ...props } = {}) {
    return async function openDiscuss() {
        const actionOpenDiscuss = {
            // hardcoded actionId, required for discuss_container props validation.
            id: 104,
            context,
            params,
            tag: 'mail.action_discuss',
            type: 'ir.actions.client',
        };
        await afterNextRender(() => doAction(webClient, actionOpenDiscuss, { props }));
    };
}

//------------------------------------------------------------------------------
// Public: start function helpers
//------------------------------------------------------------------------------

/**
 * Main function used to make a mocked environment with mocked messaging env.
 *
 * @param {Object} [param0={}]
 * @param {boolean} [param0.autoOpenDiscuss=false] determine if discuss should be
 *   open initially. Deprecated, call openDiscuss() instead.
 * @param {Object} [param0.serverData] The data to pass to the webClient
 * @param {Object} [param0.discuss={}] provide data that is passed to the discuss action.
 * @param {Object} [param0.legacyServices]
 * @param {Object} [param0.services]
 * @param {function} [param0.mockRPC]
 * @param {boolean} [param0.hasTimeControl=false] if set, all flow of time
 *   with `messaging.browser.setTimeout` are fully controlled by test itself.
 * @param {integer} [param0.loadingBaseDelayDuration=0]
 * @param {Deferred|Promise} [param0.messagingBeforeCreationDeferred=Promise.resolve()]
 *   Deferred that let tests block messaging creation and simulate resolution.
 *   Useful for testing working components when messaging is not yet created.
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
    // patch _.debounce and _.throttle to be fast and synchronous.
    patchWithCleanup(_, {
        debounce: func => func,
        throttle: func => func,
    });
    const {
        autoOpenDiscuss,
        discuss = {},
        hasTimeControl,
        waitUntilEvent,
        waitUntilMessagingCondition = 'initialized',
    } = param0;
    const target = param0['target'] || getFixture();
    param0['target'] = target;
    if (!['none', 'created', 'initialized'].includes(waitUntilMessagingCondition)) {
        throw Error(`Unknown parameter value ${waitUntilMessagingCondition} for 'waitUntilMessaging'.`);
    }
    const messagingBus = new EventBus();
    const testSetupDoneDeferred = makeDeferred();
    const afterEvent = getAfterEvent({ messagingBus });
    let waitUntilEventPromise;
    if (waitUntilEvent) {
        waitUntilEventPromise = afterEvent({ func: () => testSetupDoneDeferred.resolve(), ...waitUntilEvent, });
    } else {
        testSetupDoneDeferred.resolve();
        waitUntilEventPromise = Promise.resolve();
    }

    pyEnv = await getPyEnv();
    param0.serverData = param0.serverData || getActionManagerServerData();
    param0.serverData.models = { ...pyEnv.getData(), ...param0.serverData.models };
    param0.serverData.views = { ...pyEnv.getViews(), ...param0.serverData.views };
    const webClient = await getWebClientReady({ ...param0, messagingBus, testSetupDoneDeferred });

    const { modelManager } = webClient.env.services.messaging;
    registerCleanup(async () => {
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
    const openDiscuss = getOpenDiscuss(webClient, discuss);
    if (autoOpenDiscuss) {
        await openDiscuss();
    }
    // link the pyEnv to the actual mockServer after execution of createWebClient.
    pyEnv.mockServer = MockServer.currentMockServer;
    const openView = async (action, options) => {
        action['type'] = action['type'] || 'ir.actions.act_window';
        return doAction(webClient, action, { props: options });
    };
    await waitUntilEventPromise;
    return {
        advanceTime: hasTimeControl ? getAdvanceTime() : undefined,
        afterEvent,
        afterNextRender,
        click: getClick({ afterNextRender }),
        createChatterContainerComponent: getCreateChatterContainerComponent({ afterEvent, env: webClient.env, target }),
        createComposerComponent: getCreateComposerComponent({ env: webClient.env, modelManager, target }),
        createComposerSuggestionComponent: getCreateComposerSuggestionComponent({ env: webClient.env, modelManager, target }),
        createMessageComponent: getCreateMessageComponent({ env: webClient.env, modelManager, target }),
        createMessagingMenuComponent: getCreateMessagingMenuComponent({ env: webClient.env, target }),
        createNotificationListComponent: getCreateNotificationListComponent({ env: webClient.env, modelManager, target }),
        createRootMessagingComponent: (componentName, props) => createRootMessagingComponent(webClient.env, componentName, { props, target }),
        createThreadViewComponent: getCreateThreadViewComponent({ afterEvent, env: webClient.env, target }),
        env: webClient.env,
        insertText,
        messaging: modelManager.messaging,
        openDiscuss,
        openView,
        pyEnv,
        webClient,
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
    dragenterFiles,
    dropFiles,
    isScrolledToBottom,
    nextAnimationFrame,
    nextTick,
    pasteFiles,
    start,
};
