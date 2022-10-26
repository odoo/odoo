/** @odoo-module **/

import { getPyEnv, startServer } from '@bus/../tests/helpers/mock_python_environment';

import { nextTick } from '@mail/utils/utils';
import { getAdvanceTime } from '@mail/../tests/helpers/time_control';
import { getWebClientReady } from '@mail/../tests/helpers/webclient_setup';

import { wowlServicesSymbol } from "@web/legacy/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { getFixture, makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";

const { App, EventBus } = owl;
const { afterNextRender } = App;

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
        const error = new Error(message || `Timeout: the event ${eventName} was not triggered.`);
        // Set up the timeout to reject if the event is not triggered.
        let timeoutNoEvent;
        const timeoutProm = new Promise((resolve, reject) => {
            timeoutNoEvent = setTimeout(() => {
                console.warn(error);
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
        await Promise.race([eventProm, timeoutProm]).finally(() => {
            // Execute clean up regardless of whether the promise is
            // rejected or not.
            clearTimeout(timeoutNoEvent);
            messagingBus.removeEventListener(eventName, eventHandler);
        });
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

function getMouseenter({ afterNextRender }) {
    return async function mouseenter(selector) {
        await afterNextRender(() =>
            document.querySelector(selector).dispatchEvent(new window.MouseEvent('mouseenter'))
        );
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
        waitUntilMessagingCondition = 'initialized',
    } = param0;
    const advanceTime = hasTimeControl ? getAdvanceTime() : undefined;
    const target = param0['target'] || getFixture();
    param0['target'] = target;
    if (!['none', 'created', 'initialized'].includes(waitUntilMessagingCondition)) {
        throw Error(`Unknown parameter value ${waitUntilMessagingCondition} for 'waitUntilMessaging'.`);
    }
    const messagingBus = new EventBus();
    const afterEvent = getAfterEvent({ messagingBus });

    const pyEnv = await getPyEnv();
    param0.serverData = param0.serverData || getActionManagerServerData();
    param0.serverData.models = { ...pyEnv.getData(), ...param0.serverData.models };
    param0.serverData.views = { ...pyEnv.getViews(), ...param0.serverData.views };
    let webClient;
    await afterNextRender(async () => {
        webClient = await getWebClientReady({ ...param0, messagingBus });
        if (waitUntilMessagingCondition === 'created') {
            await webClient.env.services.messaging.modelManager.messagingCreatedPromise;
        }
        if (waitUntilMessagingCondition === 'initialized') {
            await webClient.env.services.messaging.modelManager.messagingCreatedPromise;
            await webClient.env.services.messaging.modelManager.messagingInitializedPromise;
        }
    });

    registerCleanup(async () => {
        await webClient.env.services.messaging.modelManager.messagingInitializedPromise;
        webClient.env.services.messaging.modelManager.destroy();
        delete webClient.env.services.messaging;
        delete owl.Component.env.services.messaging;
        delete owl.Component.env[wowlServicesSymbol].messaging;
        delete owl.Component.env;
    });
    const openView = async (action, options) => {
        action['type'] = action['type'] || 'ir.actions.act_window';
        await afterNextRender(() => doAction(webClient, action, { props: options }));
    };
    return {
        advanceTime,
        afterEvent,
        afterNextRender,
        click: getClick({ afterNextRender }),
        env: webClient.env,
        insertText,
        messaging: webClient.env.services.messaging.modelManager.messaging,
        mouseenter: getMouseenter({ afterNextRender }),
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
    startServer,
};
