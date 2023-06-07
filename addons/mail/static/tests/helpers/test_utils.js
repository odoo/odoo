/* @odoo-module */

import { getPyEnv, startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadEmoji } from "@mail/core/common/emoji_picker";
import { patchBrowserNotification } from "@mail/../tests/helpers/patch_notifications";
import { getAdvanceTime } from "@mail/../tests/helpers/time_control";
import { getWebClientReady } from "@mail/../tests/helpers/webclient_setup";

import { App, EventBus } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session as sessionInfo } from "@web/session";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import {
    clearRegistryWithCleanup,
    registryNamesToCloneWithCleanup,
    utils,
} from "@web/../tests/helpers/mock_env";
import { getFixture, makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";

const { prepareRegistriesWithCleanup } = utils;
const { afterNextRender } = App;

// load emoji data once, when the test suite starts.
QUnit.begin(loadEmoji);
registryNamesToCloneWithCleanup.push("mock_server_callbacks");

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
        dropEffect: "all",
        effectAllowed: "all",
        files,
        items: [],
        types: ["Files"],
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

/**
 * Wait a task tick, so that anything in micro-task queue that can be processed
 * is processed.
 */
async function nextTick() {
    await new Promise(setTimeout);
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
        const eventHandler = (ev) => {
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

function getClick({ target, afterNextRender }) {
    return async function click(selector) {
        await afterNextRender(() => {
            if (typeof selector === "string") {
                $(target ?? document.body)
                    .find(selector)[0]
                    .click();
            } else if (selector instanceof HTMLElement) {
                selector.click();
            } else {
                // jquery
                selector[0].click();
            }
        });
    };
}

function getMouseenter({ afterNextRender }) {
    return async function mouseenter(selector) {
        await afterNextRender(() =>
            document.querySelector(selector).dispatchEvent(new window.MouseEvent("mouseenter"))
        );
    };
}

function getOpenDiscuss(webClient, { context = {}, params = {}, ...props } = {}) {
    return async function openDiscuss(pActiveId, { waitUntilMessagesLoaded = true } = {}) {
        const actionOpenDiscuss = {
            // hardcoded actionId, required for discuss_container props validation.
            id: 104,
            context,
            params,
            tag: "mail.action_discuss",
            type: "ir.actions.client",
        };
        const activeId =
            pActiveId ?? context.active_id ?? params.default_active_id ?? "mail.box_inbox";
        let [threadModel, threadId] =
            typeof activeId === "number" ? ["discuss.channel", activeId] : activeId.split("_");
        if (threadModel === "discuss.channel") {
            threadId = parseInt(threadId, 10);
        }
        // TODO-DISCUSS-REFACTORING: remove when activeId will be handled.
        webClient.env.services["mail.thread"].setDiscussThread(
            webClient.env.services["mail.thread"].insert({
                model: threadModel,
                id: threadId,
            })
        );
        if (waitUntilMessagesLoaded) {
            const messagesLoadedPromise = makeDeferred();
            const store = webClient.env.services["mail.store"];
            const thread = store.threads[store.discuss.threadLocalId];
            if (thread.isLoaded) {
                messagesLoadedPromise.resolve();
            }
            let loadMessageRoute = `/mail/${threadId}/messages`;
            if (Number.isInteger(threadId)) {
                loadMessageRoute = "/discuss/channel/messages";
            }
            registry.category("mock_server_callbacks").add(
                loadMessageRoute,
                ({ channel_id: channelId = threadId }) => {
                    if (channelId === threadId) {
                        messagesLoadedPromise.resolve();
                    }
                },
                { force: true }
            );
            return afterNextRender(async () => {
                await doAction(webClient, actionOpenDiscuss, { props });
                await messagesLoadedPromise;
            });
        }
        return afterNextRender(() => doAction(webClient, actionOpenDiscuss, { props }));
    };
}

/**
 * Wait until the form view corresponding to the given resId/resModel has loaded.
 *
 * @param {Function} func Function expected to trigger form view load.
 * @param {Object} param1
 */
export function waitFormViewLoaded(
    func,
    { resId = false, resModel, waitUntilMessagesLoaded = true, waitUntilDataLoaded = true } = {}
) {
    const waitData = (func) => {
        const dataLoadedPromise = makeDeferred();
        registry.category("mock_server_callbacks").add(
            "/mail/thread/data",
            ({ thread_id: threadId, thread_model: threadModel }) => {
                if (threadId === resId && threadModel === resModel) {
                    dataLoadedPromise.resolve();
                }
            },
            { force: true }
        );
        return afterNextRender(async () => {
            await func();
            await dataLoadedPromise;
        });
    };
    const waitMessages = (func) => {
        const messagesLoadedPromise = makeDeferred();
        registry.category("mock_server_callbacks").add(
            "/mail/thread/messages",
            ({ thread_id: threadid, thread_model: threadModel }) => {
                if (threadid === resId && threadModel === resModel) {
                    messagesLoadedPromise.resolve();
                }
            },
            { force: true }
        );
        return afterNextRender(async () => {
            await func();
            await messagesLoadedPromise;
        });
    };
    if (waitUntilDataLoaded && waitUntilMessagesLoaded) {
        return waitData(() => waitMessages(func));
    }
    if (waitUntilDataLoaded) {
        return waitData(func);
    }
    if (waitUntilMessagesLoaded) {
        return waitMessages(func);
    }
}

function getOpenFormView(openView) {
    return async function openFormView(
        res_model,
        res_id,
        {
            props,
            waitUntilDataLoaded = Boolean(res_id),
            waitUntilMessagesLoaded = Boolean(res_id),
        } = {}
    ) {
        const action = {
            res_model,
            res_id,
            views: [[false, "form"]],
        };
        const func = () => openView(action, props);
        if (waitUntilDataLoaded || waitUntilMessagesLoaded) {
            return waitFormViewLoaded(func, {
                resId: res_id,
                resModel: res_model,
                waitUntilDataLoaded,
                waitUntilMessagesLoaded,
            });
        }
        return func();
    };
}

//------------------------------------------------------------------------------
// Public: start function helpers
//------------------------------------------------------------------------------

/**
 * Reset registries used by the messaging environment. Useful to create multiple
 * web clients.
 */
function resetRegistries() {
    const categories = [
        "actions",
        "main_components",
        "services",
        "systray",
        "wowlToLegacyServiceMappers",
    ];
    for (const name of categories) {
        clearRegistryWithCleanup(registry.category(name));
    }
    prepareRegistriesWithCleanup();
}

let tabs = [];
registerCleanup(() => (tabs = []));
/**
 * Add an item to the "Switch Tab" dropdown. If it doesn't exist, create the
 * dropdown and add the item afterwards.
 *
 * @param {HTMLElement} rootTarget Where to mount the dropdown menu.
 * @param {HTMLElement} tabTarget Tab to switch to when clicking on the dropdown
 * item.
 */
async function addSwitchTabDropdownItem(rootTarget, tabTarget) {
    tabs.push(tabTarget);
    const zIndexMainTab = 100000;
    let dropdownDiv = rootTarget.querySelector(".o-mail-multi-tab-dropdown");
    if (!dropdownDiv) {
        tabTarget.style.zIndex = zIndexMainTab;
        dropdownDiv = document.createElement("div");
        dropdownDiv.style.zIndex = zIndexMainTab + 1;
        dropdownDiv.style.top = "10%";
        dropdownDiv.style.right = "5%";
        dropdownDiv.style.position = "absolute";
        dropdownDiv.classList.add("dropdown");
        dropdownDiv.classList.add("o-mail-multi-tab-dropdown");
        dropdownDiv.innerHTML = `
            <button class="btn btn-primary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                Switch Tab (${tabs.length})
            </button>
            <ul class="dropdown-menu"></ul>
        `;
        rootTarget.appendChild(dropdownDiv);
    }
    const tabIndex = tabs.length;
    const li = document.createElement("li");
    const a = document.createElement("a");
    li.appendChild(a);
    a.classList.add("dropdown-item");
    a.innerText = `Tab ${tabIndex}`;
    browser.addEventListener("click", (ev) => {
        const link = ev.target.closest(".dropdown-item");
        if (a.isEqualNode(link)) {
            tabs.forEach((tab) => (tab.style.zIndex = 0));
            tabTarget.style.zIndex = zIndexMainTab;
            dropdownDiv.querySelector(".dropdown-toggle").innerText = `Switch Tab (${tabIndex})`;
        }
    });
    dropdownDiv.querySelector(".dropdown-menu").appendChild(li);
}

/**
 * Main function used to make a mocked environment with mocked messaging env.
 *
 * @param {Object} [param0={}]
 * @param {boolean} [param0.asTab] Whether or not the resulting WebClient should
 * be considered as a separate tab.
 * @param {Object} [param0.serverData] The data to pass to the webClient
 * @param {Object} [param0.discuss={}] provide data that is passed to the
 * discuss action.
 * @param {Object} [param0.legacyServices]
 * @param {Object} [param0.services]
 * @param {function} [param0.mockRPC]
 * @param {boolean} [param0.hasTimeControl=false] if set, all flow of time with
 *   `messaging.browser.setTimeout` are fully controlled by test itself.
 * @param {integer} [param0.loadingBaseDelayDuration=0]
 * @returns {Object}
 */
async function start(param0 = {}) {
    const { discuss = {}, hasTimeControl } = param0;
    const advanceTime = hasTimeControl ? getAdvanceTime() : undefined;
    let target = param0["target"] || getFixture();
    if (param0.asTab) {
        resetRegistries();
        const rootTarget = target;
        target = document.createElement("div");
        target.style.width = "100%";
        rootTarget.appendChild(target);
        addSwitchTabDropdownItem(rootTarget, target);
    }
    // make qunit fixture in visible range,
    // so that features like IntersectionObserver work as expected
    target.style.position = "absolute";
    target.style.top = "0";
    target.style.left = "0";
    target.style.height = "100%";
    target.style.opacity = QUnit.config.debug ? "" : "0";
    registerCleanup(async () => {
        target.style.position = "";
        target.style.top = "";
        target.style.left = "";
        target.style.height = "";
        target.style.opacity = "";
    });
    param0["target"] = target;
    const messagingBus = new EventBus();
    const afterEvent = getAfterEvent({ messagingBus });

    const pyEnv = await getPyEnv();
    patchWithCleanup(sessionInfo, {
        user_context: {
            ...sessionInfo.user_context,
            uid: pyEnv.currentUserId,
        },
        uid: pyEnv.currentUserId,
        partner_id: pyEnv.currentPartnerId,
    });
    if (browser.Notification && !browser.Notification.isPatched) {
        patchBrowserNotification("denied");
    }
    param0.serverData = param0.serverData || getActionManagerServerData();
    param0.serverData.models = { ...pyEnv.getData(), ...param0.serverData.models };
    param0.serverData.views = { ...pyEnv.getViews(), ...param0.serverData.views };
    let webClient;
    await afterNextRender(async () => {
        webClient = await getWebClientReady({ ...param0, messagingBus });
    });
    if (webClient.env.services.ui.isSmall) {
        target.style.width = "100%";
    }
    const openView = async (action, options) => {
        action["type"] = action["type"] || "ir.actions.act_window";
        await afterNextRender(() => doAction(webClient, action, { props: options }));
    };
    return {
        advanceTime,
        afterEvent,
        afterNextRender,
        click: getClick({ target, afterNextRender }),
        env: webClient.env,
        insertText,
        mouseenter: getMouseenter({ afterNextRender }),
        openDiscuss: getOpenDiscuss(webClient, discuss),
        openView,
        openFormView: getOpenFormView(openView),
        pyEnv,
        target,
        webClient,
    };
}

//------------------------------------------------------------------------------
// Public: file utilities
//------------------------------------------------------------------------------

/**
 * Create a file object, which can be used for drag-and-drop.
 *
 * @param {Object} data
 * @param {string} data.name
 * @param {string} data.content
 * @param {string} data.contentType
 * @returns {Promise<Object>} resolved with file created
 */
export function createFile(data) {
    // Note: this is only supported by Chrome, and does not work in Incognito mode
    return new Promise(function (resolve, reject) {
        const requestFileSystem = window.requestFileSystem || window.webkitRequestFileSystem;
        if (!requestFileSystem) {
            throw new Error("FileSystem API is not supported");
        }
        requestFileSystem(window.TEMPORARY, 1024 * 1024, function (fileSystem) {
            fileSystem.root.getFile(data.name, { create: true }, function (fileEntry) {
                fileEntry.createWriter(function (fileWriter) {
                    fileWriter.onwriteend = function (e) {
                        fileSystem.root.getFile(data.name, {}, function (fileEntry) {
                            fileEntry.file(function (file) {
                                resolve(file);
                            });
                        });
                    };
                    fileWriter.write(new Blob([data.content], { type: data.contentType }));
                });
            });
        });
    });
}

/**
 * Drag some files over a DOM element
 *
 * @param {DOM.Element} el
 * @param {Object[]} file must have been create beforehand
 *   @see testUtils.file.createFile
 */
function dragenterFiles(el, files) {
    const ev = new Event("dragenter", { bubbles: true });
    Object.defineProperty(ev, "dataTransfer", {
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
    const ev = new Event("drop", { bubbles: true });
    Object.defineProperty(ev, "dataTransfer", {
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
    const ev = new Event("paste", { bubbles: true });
    Object.defineProperty(ev, "clipboardData", {
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
 * @param {Object} [param2 = {}]
 * @param {boolean} [param2.replace = false]
 */
export async function insertText(selector, content, { replace = false } = {}) {
    await afterNextRender(() => {
        if (replace) {
            document.querySelector(selector).value = "";
        }
        document.querySelector(selector).focus();
        for (const char of content) {
            document.execCommand("insertText", false, char);
            document
                .querySelector(selector)
                .dispatchEvent(new window.KeyboardEvent("keydown", { key: char }));
            document
                .querySelector(selector)
                .dispatchEvent(new window.KeyboardEvent("keyup", { key: char }));
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

/**
 * Determine if a DOM element is scrolled to the given scroll top position.
 *
 * A 1px margin of error is given to accomodate subpixel rounding issues and
 * Element.scrollHeight value being either int or decimal
 *
 * @param {DOM.Element} el
 * @param {number} scrollTop expected scroll top value.
 * @returns {boolean}
 */
function isScrolledTo(el, scrollTop) {
    return Math.abs(el.scrollTop - scrollTop) <= 1;
}
//------------------------------------------------------------------------------
// Public: web API utilities
//------------------------------------------------------------------------------

/**
 * Mocks the browser's `navigator.mediaDevices.getUserMedia` and `navigator.mediaDevices.getDisplayMedia`
 */
export function mockGetMedia() {
    class MockMediaStreamTrack extends EventTarget {
        enabled = true;
        readyState = "live";
        constructor(kind) {
            super();
            this.kind = kind;
        }
        stop() {
            this.readyState = "ended";
        }
    }
    /**
     * The audio streams are mocked as there is no way to create a MediaStream
     * with an audio track without really requesting it from the device.
     */
    class MockAudioMediaStream extends MediaStream {
        mockTracks = [new MockMediaStreamTrack("audio")];
        getTracks() {
            return this.mockTracks;
        }
        getAudioTracks() {
            return this.mockTracks;
        }
        getVideoTracks() {
            return [];
        }
    }
    const streams = [];
    /**
     * The video streams are real MediaStreams created from a 1x1 canvas at 1fps.
     */
    const createVideoStream = (constraints) => {
        const canvas = document.createElement("canvas");
        canvas.width = 1;
        canvas.height = 1;
        const stream = canvas.captureStream(1);
        return stream;
    };
    patchWithCleanup(browser.navigator.mediaDevices, {
        getUserMedia(constraints) {
            let stream;
            if (constraints.audio) {
                stream = new MockAudioMediaStream();
            } else {
                // The video streams are real MediaStreams
                stream = createVideoStream();
            }
            streams.push(stream);
            return stream;
        },
        getDisplayMedia() {
            const stream = createVideoStream();
            streams.push(stream);
            return stream;
        },
    });
    registerCleanup(() => {
        // stop all streams as some tests may not do actions that lead to the ending of tracks
        streams.forEach((stream) => {
            stream.getTracks().forEach((track) => track.stop());
        });
    });
}
//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

export {
    afterNextRender,
    dragenterFiles,
    dropFiles,
    isScrolledToBottom,
    isScrolledTo,
    nextAnimationFrame,
    nextTick,
    pasteFiles,
    start,
    startServer,
};

export const click = getClick({ afterNextRender });

/**
 * Function that wait until a selector is present in the DOM
 *
 * @param {string} selector
 */
export function waitUntil(selector, count = 1) {
    return new Promise((resolve, reject) => {
        if ($(selector).length === count) {
            return resolve($(selector));
        }
        const timer = setTimeout(() => {
            observer.disconnect();
            reject(new Error(`Waited 5 second for ${selector}`));
            console.error(`Waited 5 second for ${selector}`);
        }, 5000);
        const observer = new MutationObserver((mutations) => {
            if ($(selector).length === count) {
                resolve($(selector));
                observer.disconnect();
                clearTimeout(timer);
            }
        });

        observer.observe(document.body, {
            attributes: true,
            childList: true,
            subtree: true,
        });
    });
}
