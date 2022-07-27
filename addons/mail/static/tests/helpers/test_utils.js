/** @odoo-module **/

import { nextTick } from '@mail/utils/utils';
import { getAdvanceTime } from '@mail/../tests/helpers/time_control';
import { getWebClientReady } from '@mail/../tests/helpers/webclient_setup';

import { registry } from '@web/core/registry';
import { wowlServicesSymbol } from "@web/legacy/utils";
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
        const viewArchsSubRegistries = registry.category('mail.view.archs').subRegistries;
        for (const [viewType, archsRegistry] of Object.entries(viewArchsSubRegistries)) {
            views[`${modelName},false,${viewType}`] =
                archsRegistry.get(modelName, archsRegistry.get('default'));
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
                    create(values) {
                        if (!values) {
                            return;
                        }
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
        const eventProm = makeDeferred();
        const eventHandler = ev => {
            if (!predicate || predicate(ev.detail)) {
                eventProm.resolve();
            }
        };
        messagingBus.addEventListener(eventName, eventHandler);
        // Start the function expected to trigger the event after the
        // promise has been registered to not miss any potential event.
        const funcRes = func();
        // Make them race (first to resolve/reject wins).
        await Promise.race([eventProm, timeoutProm]);
        clearTimeout(timeoutNoEvent);
        messagingBus.removeEventListener(eventName, eventHandler);
        // If the event is triggered before the end of the async function,
        // ensure the function finishes its job before returning.
        return await funcRes;
    };
}

function getClick({ afterNextRender }) {
    return async function click(selector) {
        await afterNextRender(() => document.querySelector(selector).click());
    };
}

function getOpenDiscuss(afterEvent, webClient, { context = {}, params, ...props } = {}) {
    return async function openDiscuss({ waitUntilMessagesLoaded = true } = {}) {
        const actionOpenDiscuss = {
            // hardcoded actionId, required for discuss_container props validation.
            id: 104,
            context,
            params,
            tag: 'mail.action_discuss',
            type: 'ir.actions.client',
        };
        if (waitUntilMessagesLoaded) {
            let threadId = context.active_id;
            if (typeof threadId === 'string') {
                threadId = parseInt(threadId.split('_')[1]);
            }
            return afterNextRender(() => afterEvent({
                eventName: 'o-thread-view-hint-processed',
                func: () => doAction(webClient, actionOpenDiscuss, { props }),
                message: "should wait until discuss loaded its messages",
                predicate: ({ hint, threadViewer }) => {
                    return (
                        hint.type === 'messages-loaded' &&
                        (!threadId || threadViewer.thread.id === threadId)
                    );
                },
            }));
        }
        return afterNextRender(() => doAction(webClient, actionOpenDiscuss, { props }));
    };
}

function getOpenFormView(afterEvent, openView) {
    return async function openFormView(action, { props, waitUntilDataLoaded = true, waitUntilMessagesLoaded = true } = {}) {
        action['views'] = [[false, 'form']];
        const func = () => openView(action, props);
        const waitData = func => afterNextRender(() => afterEvent({
            eventName: 'o-thread-loaded-data',
            func,
            message: "should wait until chatter loaded its data",
            predicate: ({ thread }) => {
                return (
                    thread.model === action.res_model &&
                    thread.id === action.res_id
                );
            },
        }));
        const waitMessages = func => afterNextRender(() => afterEvent({
            eventName: 'o-thread-loaded-messages',
            func,
            message: "should wait until chatter loaded its messages",
            predicate: ({ thread }) => {
                return (
                    thread.model === action.res_model &&
                    thread.id === action.res_id
                );
            },
        }));
        if (waitUntilDataLoaded && waitUntilMessagesLoaded) {
            return waitData(() => waitMessages(func));
        }
        if (waitUntilDataLoaded) {
            return waitData(func);
        }
        if (waitUntilMessagesLoaded) {
            return waitMessages(func);
        }
        return func();
    };
}

//------------------------------------------------------------------------------
// Public: start function helpers
//------------------------------------------------------------------------------

/**
 * Main function used to make a mocked environment with mocked messaging env.
 *
 * @param {Object} [param0={}]
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
        discuss = {},
        hasTimeControl,
        waitUntilEvent,
        waitUntilMessagingCondition = 'initialized',
    } = param0;
    const advanceTime = hasTimeControl ? getAdvanceTime() : undefined;
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

    webClient.env.services.messaging.modelManager;
    registerCleanup(async () => {
        await webClient.env.services.messaging.modelManager.messagingInitializedPromise;
        webClient.env.services.messaging.modelManager.destroy();
        delete webClient.env.services.messaging;
        delete owl.Component.env.services.messaging;
        delete owl.Component.env[wowlServicesSymbol].messaging;
        delete owl.Component.env;
    });
    if (waitUntilMessagingCondition === 'created') {
        await webClient.env.services.messaging.modelManager.messagingCreatedPromise;
    }
    if (waitUntilMessagingCondition === 'initialized') {
        await webClient.env.services.messaging.modelManager.messagingCreatedPromise;
        await webClient.env.services.messaging.modelManager.messagingInitializedPromise;
    }
    // link the pyEnv to the actual mockServer after execution of createWebClient.
    pyEnv.mockServer = MockServer.currentMockServer;
    const openView = async (action, options) => {
        action['type'] = action['type'] || 'ir.actions.act_window';
        await afterNextRender(() => doAction(webClient, action, { props: options }));
    };
    await waitUntilEventPromise;
    return {
        advanceTime,
        afterEvent,
        afterNextRender,
        click: getClick({ afterNextRender }),
        env: webClient.env,
        insertText,
        messaging: webClient.env.services.messaging.modelManager.messaging,
        openDiscuss: getOpenDiscuss(afterEvent, webClient, discuss),
        openView,
        openFormView: getOpenFormView(afterEvent, openView),
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
