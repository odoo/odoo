import { addBusMessageHandler, busModels } from "@bus/../tests/bus_test_helpers";
import { after, before, expect, getFixture, registerDebugInfo, test } from "@odoo/hoot";
import { hover as hootHover, queryFirst, resize } from "@odoo/hoot-dom";
import { Deferred, microTick } from "@odoo/hoot-mock";
import {
    MockServer,
    asyncStep,
    authenticate,
    defineModels,
    defineParams,
    getMockEnv,
    getService,
    makeMockEnv,
    makeMockServer,
    mountWithCleanup,
    onRpc,
    parseViewProps,
    patchWithCleanup,
    restoreRegistry,
    serverState,
    waitForSteps,
    webModels,
} from "@web/../tests/web_test_helpers";

import { CHAT_HUB_KEY } from "@mail/core/common/chat_hub_model";
import { click, contains } from "./mail_test_helpers_contains";

import { closeStream, mailGlobal } from "@mail/utils/common/misc";
import { Component, onMounted, onPatched, onWillDestroy, status } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { registry } from "@web/core/registry";
import { MEDIAS_BREAKPOINTS, utils as uiUtils } from "@web/core/ui/ui_service";
import { useServiceProtectMethodHandling } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { WebClient } from "@web/webclient/webclient";
export { SIZES } from "@web/core/ui/ui_service";

import {
    DISCUSS_ACTION_ID,
    authenticateGuest,
    mailDataHelpers,
} from "./mock_server/mail_mock_server";
import { Base } from "./mock_server/mock_models/base";
import { DiscussChannel } from "./mock_server/mock_models/discuss_channel";
import { DiscussChannelMember } from "./mock_server/mock_models/discuss_channel_member";
import { DiscussChannelRtcSession } from "./mock_server/mock_models/discuss_channel_rtc_session";
import { DiscussGifFavorite } from "./mock_server/mock_models/discuss_gif_favorite";
import { DiscussVoiceMetadata } from "./mock_server/mock_models/discuss_voice_metadata";
import { IrAttachment } from "./mock_server/mock_models/ir_attachment";
import { IrWebSocket } from "./mock_server/mock_models/ir_websocket";
import { M2xAvatarUser } from "./mock_server/mock_models/m2x_avatar_user";
import { MailActivity } from "./mock_server/mock_models/mail_activity";
import { MailActivitySchedule } from "./mock_server/mock_models/mail_activity_schedule";
import { MailActivityType } from "./mock_server/mock_models/mail_activity_type";
import { MailCannedResponse } from "./mock_server/mock_models/mail_canned_response";
import { MailComposeMessage } from "./mock_server/mock_models/mail_composer_message";
import { MailFollowers } from "./mock_server/mock_models/mail_followers";
import { MailGuest } from "./mock_server/mock_models/mail_guest";
import { MailLinkPreview } from "./mock_server/mock_models/mail_link_preview";
import { MailMessage } from "./mock_server/mock_models/mail_message";
import { MailMessageLinkPreview } from "./mock_server/mock_models/mail_message_link_preview";
import { MailMessageReaction } from "./mock_server/mock_models/mail_message_reaction";
import { MailMessageSubtype } from "./mock_server/mock_models/mail_message_subtype";
import { MailNotification } from "./mock_server/mock_models/mail_notification";
import { MailPushDevice } from "./mock_server/mock_models/mail_push_device";
import { MailScheduledMessage } from "./mock_server/mock_models/mail_scheduled_message";
import { MailTemplate } from "./mock_server/mock_models/mail_template";
import { MailThread } from "./mock_server/mock_models/mail_thread";
import { MailTrackingValue } from "./mock_server/mock_models/mail_tracking_value";
import { ResCountry } from "./mock_server/mock_models/res_country";
import { ResFake } from "./mock_server/mock_models/res_fake";
import { ResLang } from "./mock_server/mock_models/res_lang";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { ResRole } from "./mock_server/mock_models/res_role";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { ResUsersSettings } from "./mock_server/mock_models/res_users_settings";
import { ResUsersSettingsVolumes } from "./mock_server/mock_models/res_users_settings_volumes";
import { Network, Rtc } from "@mail/discuss/call/common/rtc_service";
import { UPDATE_EVENT } from "@mail/discuss/call/common/peer_to_peer";

export * from "./mail_test_helpers_contains";

before(prepareRegistriesWithCleanup);
export const registryNamesToCloneWithCleanup = [];
registryNamesToCloneWithCleanup.push("mock_server_callbacks", "discuss.model");

mailGlobal.isInTest = true;
useServiceProtectMethodHandling.fn = useServiceProtectMethodHandling.mocked; // so that RPCs after tests do not throw error

addBusMessageHandler("mail.record/insert", (_env, _id, payload) => {
    const recordsByModelName = Object.entries(payload);
    for (const [modelName, records] of recordsByModelName) {
        for (const record of Array.isArray(records) ? records : [records]) {
            registerDebugInfo(`insert > "${modelName}"`, record);
        }
    }
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function defineMailModels() {
    defineParams({ suite: "mail" }, "replace");
    return defineModels(mailModels);
}

export function getChannelCommandsForThread(threadId) {
    const store = getService("mail.store");
    const suggestionService = getService("mail.suggestion");
    const thread = store.Thread.get({ model: "discuss.channel", id: threadId });
    return suggestionService.getChannelCommands(thread);
}

export const mailModels = {
    ...webModels,
    ...busModels,
    Base,
    DiscussChannel,
    DiscussChannelMember,
    DiscussChannelRtcSession,
    DiscussGifFavorite,
    DiscussVoiceMetadata,
    IrAttachment,
    IrWebSocket,
    M2xAvatarUser,
    MailActivity,
    MailActivitySchedule,
    MailActivityType,
    MailComposeMessage,
    MailCannedResponse,
    MailFollowers,
    MailGuest,
    MailLinkPreview,
    MailMessage,
    MailMessageLinkPreview,
    MailMessageReaction,
    MailMessageSubtype,
    MailNotification,
    MailPushDevice,
    MailScheduledMessage,
    MailTemplate,
    MailThread,
    MailTrackingValue,
    ResCountry,
    ResFake,
    ResLang,
    ResPartner,
    ResRole,
    ResUsers,
    ResUsersSettings,
    ResUsersSettingsVolumes,
};

/**
 * Register a callback to be executed before an RPC request is processed.
 *
 * @param {Function|string} route
 * - If a function is provided, it will be executed for every RPC call.
 * - If a string is provided, the callback will only be executed if the RPC
 *   route matches the provided string.
 * @param {Function} callback - The function to execute before the RPC call.
 */
export function onRpcBefore(route, callback) {
    if (typeof route === "string") {
        const handler = registry.category("mail.mock_rpc").get(route);
        patchWithCleanup(handler, { before: callback });
    } else {
        const onRpcBeforeGlobal = registry.category("mail.on_rpc_before_global").get(true);
        patchWithCleanup(onRpcBeforeGlobal, { cb: route });
    }
}

/**
 * Register a callback to be executed just before end of an RPC request being processed.
 * Useful to do all server processing but delay the response received by web client.
 *
 * @param {string} route the route to put callback just before returning response.
 * @param {Function} callback - The function to execute just before the end of RPC call.
 */
export function onRpcAfter(route, callback) {
    const handler = registry.category("mail.mock_rpc").get(route);
    patchWithCleanup(handler, { after: callback });
}

let archs = {};
export function registerArchs(newArchs) {
    archs = newArchs;
    after(() => (archs = {}));
}

export function onlineTest(...args) {
    if (navigator.onLine) {
        return test(...args);
    } else {
        return test.skip(...args);
    }
}

export async function openDiscuss(activeId, { target } = {}) {
    const actionService = target?.services.action ?? getService("action");
    await actionService.doAction({
        context: { active_id: activeId },
        id: DISCUSS_ACTION_ID,
        tag: "mail.action_discuss",
        type: "ir.actions.client",
    });
}

export async function openFormView(resModel, resId, params) {
    return openView({
        res_model: resModel,
        res_id: resId,
        views: [[false, "form"]],
        ...params,
    });
}

export async function openKanbanView(resModel, params) {
    return openView({
        res_model: resModel,
        views: [[false, "kanban"]],
        ...params,
    });
}

export async function openListView(resModel, params) {
    return openView({
        res_model: resModel,
        views: [[false, "list"]],
        ...params,
    });
}

export async function openView({ context, res_model, res_id, views, domain, ...params }) {
    const [[viewId, type]] = views;
    const action = {
        context,
        domain,
        res_model,
        res_id,
        views: [[viewId, type]],
        type: "ir.actions.act_window",
    };
    const options = parseViewProps({
        type,
        resModel: res_model,
        resId: res_id,
        arch: params?.arch || archs[viewId || res_model + `,false,` + type] || undefined,
        viewId: params?.arch || viewId,
        ...params,
    });
    await getService("action").doAction(action, { props: options });
}

let tabs = [];
after(() => (tabs = []));
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
    const onClickDropdownItem = (e) => {
        const dropdownToggle = dropdownDiv.querySelector(".dropdown-toggle");
        dropdownToggle.innerText = `Switch Tab (${e.target.innerText})`;
        tabs.forEach((tab) => (tab.style.zIndex = -zIndexMainTab));
        if (e.target.innerText !== "Hoot") {
            tabTarget.style.zIndex = zIndexMainTab;
        }
    };
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
            <ul class="dropdown-menu">
                <li><a class="dropdown-item">Hoot</a></li>
            </ul>
        `;
        dropdownDiv.querySelector("a").onclick = onClickDropdownItem;
        rootTarget.appendChild(dropdownDiv);
    }
    const tabIndex = tabs.length;
    const li = document.createElement("li");
    const a = document.createElement("a");
    li.appendChild(a);
    a.classList.add("dropdown-item");
    a.innerText = `Tab ${tabIndex}`;
    a.onclick = onClickDropdownItem;
    dropdownDiv.querySelector(".dropdown-menu").appendChild(li);
}

let discussAsTabId = 0;

/**
 * @param {{
 *  asTab?: boolean;
 *  authenticateAs?: any | { login: string; password: string; };
 *  env?: Partial<OdooEnv>;
 * }} [options]
 */
export async function start(options) {
    patchWithCleanup(Rtc.prototype, {
        start() {
            super.start();
            after(() => this.clear());
        },
    });
    if (!MockServer.current) {
        await startServer();
    }
    let target = getFixture();
    const pyEnv = MockServer.env;
    if (options?.authenticateAs !== undefined) {
        if (options.authenticateAs === false) {
            // no authentication => new guest
            const guestId = pyEnv["mail.guest"].create({});
            authenticateGuest(pyEnv["mail.guest"].read(guestId)[0]);
        } else if (options.authenticateAs._name === "mail.guest") {
            authenticateGuest(options.authenticateAs);
        } else {
            authenticate(options.authenticateAs.login, options.authenticateAs.password);
        }
    } else if ("res.users" in pyEnv) {
        if (pyEnv.cookie.get("dgid")) {
            // already authenticated as guest
        } else {
            const adminUser = pyEnv["res.users"].search_read([["id", "=", serverState.userId]])[0];
            authenticate(adminUser.login, adminUser.password);
        }
    }
    if ("res.users" in pyEnv) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = pyEnv["res.users"];
        const store = new mailDataHelpers.Store();
        ResUsers._init_store_data(store);
        patchWithCleanup(session, {
            storeData: store.get_result(),
        });
        registerDebugInfo("session.storeData", session.storeData);
    }
    let env;
    if (options?.asTab) {
        discussAsTabId++;
        restoreRegistry(registry);
        const rootTarget = target;
        target = document.createElement("div");
        target.classList.add("o-mail-Discuss-asTabContainer");
        target.dataset.asTabId = discussAsTabId;
        rootTarget.appendChild(target);
        addSwitchTabDropdownItem(rootTarget, target);
        const selector = `.o-mail-Discuss-asTabContainer[data-as-tab-id="${target.dataset.asTabId}"]`;
        env = await makeMockEnv({ discussAsTabId, selector }, { makeNew: true });
    } else {
        env = getMockEnv() || (await makeMockEnv({}));
    }
    env.testEnv = true;
    await mountWithCleanup(WebClient, { env, target });
    await loadEmoji();
    return Object.assign(env, { ...options?.env, target });
}

export async function startServer() {
    const { env: pyEnv } = await makeMockServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupId]])
            .map(({ id }) => id),
    });
    return pyEnv;
}

/**
 * Return the width corresponding to the given size. If an upper and lower bound
 * are defined, returns the lower bound: this is an arbitrary choice that should
 * not impact anything. A test should pass the `width` parameter instead of `size`
 * if it needs a specific width to be set.
 *
 * @param {number} size
 * @returns {number} The width corresponding to the given size.
 */
function getWidthFromSize(size) {
    const { minWidth, maxWidth } = MEDIAS_BREAKPOINTS[size];
    return minWidth ? minWidth : maxWidth;
}

/**
 * Return the size corresponding to the given width.
 *
 * @param {number} width
 * @returns {number} The size corresponding to the given width.
 */
function getSizeFromWidth(width) {
    return MEDIAS_BREAKPOINTS.findIndex(({ minWidth, maxWidth }) => {
        if (!maxWidth) {
            return width >= minWidth;
        }
        if (!minWidth) {
            return width <= maxWidth;
        }
        return width >= minWidth && width <= maxWidth;
    });
}

/**
 * Adjust ui size either from given size (mapped to window breakpoints) or
 * width. This will impact uiService.{isSmall/size}, (wowl/legacy)
 * browser.innerWidth, (wowl) env.isSmall and. When a size is given, the browser
 * width is set according to the breakpoints that are used by the webClient.
 *
 * @param {Object} params parameters to configure the ui size.
 * @param {number|undefined} [params.size]
 * @param {number|undefined} [params.width]
 * @param {number|undefined} [params.height]
 */
export async function patchUiSize({ height, size, width }) {
    if ((!size && !width) || (size && width)) {
        throw new Error("Either size or width must be given to the patchUiSize function");
    }
    size = size === undefined ? getSizeFromWidth(width) : size;
    width = width || getWidthFromSize(size);

    patchWithCleanup(uiUtils, {
        getSize() {
            return size;
        },
    });

    await resize({ width, height });
}

function createAudioStream() {
    const ctx = new window.AudioContext();
    const dest = ctx.createMediaStreamDestination();
    after(() => {
        closeStream(dest.stream);
        ctx.close().catch(() => {});
    });
    return dest.stream;
}

export function createVideoStream() {
    const canvas = document.createElement("canvas");
    canvas.width = 1;
    canvas.height = 1;
    const stream = canvas.captureStream();
    after(() => closeStream(stream));
    return stream;
}

/**
 * Mocks the browser's `navigator.mediaDevices.getUserMedia` and `navigator.mediaDevices.getDisplayMedia`
 * Also mocks the permissions API to return "granted" for camera and microphone permissions by default.
 */
export function mockGetMedia() {
    const streams = [];
    // Mock permissions API to return "granted" by default.
    patchWithCleanup(browser.navigator.permissions, {
        async query() {
            return {
                state: "granted",
                addEventListener: () => {},
                removeEventListener: () => {},
                onchange: null,
            };
        },
    });
    patchWithCleanup(browser.navigator.mediaDevices, {
        getUserMedia(constraints) {
            if (constraints.audio) {
                const audioStream = createAudioStream();
                streams.push(audioStream);
                return audioStream;
            } else {
                const videoStream = createVideoStream();
                streams.push(videoStream);
                return videoStream;
            }
        },
        getDisplayMedia: () => {
            const videoStream = createVideoStream();
            streams.push(videoStream);
            return videoStream;
        },
    });
    return streams;
}

/**
 * A MockRemote represents the network API of a remote user, for example calling remote.updateUpload() behaves as if that remote user
 * had called this function on their own rtc_service.network
 *
 * @typedef {Object} MockRemote
 * @property {number} sessionId
 * @property {function(string):Promise} updateConnectionState (emits "update" event)
 * @property {function(import("@mail/discuss/call/common/rtc_service").streamType,MediaStreamTrack):Promise} updateUpload (emits "update" event)
 * @property {function(import("@mail/discuss/call/common/rtc_session_model").SessionInfo):Promise} updateInfo (emits "update" event)
 */

/**
 * @typedef {Object} MockNetwork
 * @property { function(number): MockRemote } makeMockRemote
 */

/**
 * Mocks {import("@mail/discuss/call/common/rtc_service").Network} and allows testing of features that rely on network behavior, such
 * as other participants changing the state of their microphone, sharing screen,...
 *
 * @param {Object} param0
 * @param {Partial<OdooEnv>} param0.env
 * @param {number} param0.channelId
 * @returns {Promise<MockNetwork>}
 */
export async function makeMockRtcNetwork({ env, channelId }) {
    const mockNetwork = new EventTarget();
    const pyEnv = MockServer.current.env;
    const rtc = env.services["discuss.rtc"];
    const dispatchUpdate = (payload) => {
        mockNetwork.dispatchEvent(new CustomEvent("update", { detail: payload }));
    };
    const rtcServiceIsListening = new Deferred();
    patchWithCleanup(Network.prototype, {
        addEventListener(name, f) {
            if (name === "update") {
                rtcServiceIsListening.resolve();
                // disabling the p2p network so that it does not try to send webRTC events like candidates and offers.
                rtc.network.p2p.disconnect();
            }
            mockNetwork.addEventListener(name, f);
            after(() => mockNetwork.removeEventListener(name, f));
        },
    });

    return {
        makeMockRemote(channelMemberId) {
            const sessionId = pyEnv["discuss.channel.rtc.session"].create({
                channel_member_id: channelMemberId,
                channel_id: channelId,
            });
            return {
                sessionId,
                async updateConnectionState(state) {
                    await rtcServiceIsListening;
                    dispatchUpdate({
                        name: UPDATE_EVENT.CONNECTION_CHANGE,
                        payload: {
                            id: sessionId,
                            state,
                        },
                    });
                },
                async updateInfo(info) {
                    await rtcServiceIsListening;
                    dispatchUpdate({
                        name: UPDATE_EVENT.INFO_CHANGE,
                        payload: { [sessionId]: info },
                    });
                },
                async updateUpload(type, track) {
                    await rtcServiceIsListening;
                    dispatchUpdate({
                        name: UPDATE_EVENT.TRACK,
                        payload: {
                            sessionId,
                            type,
                            track,
                            active: Boolean(track),
                        },
                    });
                },
            };
        },
    };
}

/**
 * Patch both the `Notification` and the `Permissions` API which are codependent
 * based on the given value. Note that when `requestPermissionResult` is passed,
 * the `change` event of the `Permissions` API will also be triggered.
 *
 * @param {"default" | "denied" | "granted"} permission
 * @param {"default" | "denied" | "granted"} requestPermissionResult
 */
export function patchBrowserNotification(permission = "default", requestPermissionResult) {
    if (!browser.Notification || !browser.navigator.permissions) {
        return;
    }
    const notificationQueries = [];
    patchWithCleanup(browser.navigator.permissions, {
        async query({ name }) {
            const result = await super.query(...arguments);
            if (name === "notifications") {
                Object.defineProperty(result, "state", {
                    get: () => (permission === "default" ? "prompt" : permission),
                });
                notificationQueries.push(result);
            }
            return result;
        },
    });
    patchWithCleanup(browser.Notification, {
        permission,
        isPatched: true,
        requestPermission() {
            if (!requestPermissionResult) {
                return super.requestPermission(...arguments);
            }
            this.permission = requestPermissionResult;
            for (const query of notificationQueries) {
                query.permission = requestPermissionResult;
                query.dispatchEvent(new Event("change"));
            }
            return requestPermissionResult;
        },
    });
}

function cloneRegistryWithCleanup(registry) {
    prepareRegistry(registry, { keepContent: true });
}

function prepareRegistry(registry, { keepContent = false } = {}) {
    const _addEventListener = registry.addEventListener.bind(registry);
    const _removeEventListener = registry.removeEventListener.bind(registry);
    const patch = {
        content: keepContent ? { ...registry.content } : {},
        elements: null,
        entries: null,
        subRegistries: {},
        addEventListener(type, callback) {
            _addEventListener(type, callback);
            after(() => {
                _removeEventListener(type, callback);
            });
        },
    };
    patchWithCleanup(registry, patch);
}

export function prepareRegistriesWithCleanup() {
    // Clone registries
    registryNamesToCloneWithCleanup.forEach((registryName) =>
        cloneRegistryWithCleanup(registry.category(registryName))
    );
}

const observeRenderResults = new Map();
let nextObserveRenderResults = 0;
/**
 * Patch component `onWillRender` to track amount of renders.
 * This only prepares with the patching. To effectively observe the amount of renders,
 * should call @see observeRenders
 * Having both function allow to track renders as side-effect on specific actions, rather
 * than aggregate all renders including setup: as this value requires some thinking on
 * which render comes from what, usually the less with brief explanations the better.
 */
export function prepareObserveRenders() {
    patchWithCleanup(Component.prototype, {
        setup(...args) {
            const cb = () => {
                for (const result of observeRenderResults.values()) {
                    if (!result.has(this.constructor)) {
                        result.set(this.constructor, 0);
                    }
                    result.set(this.constructor, result.get(this.constructor) + 1);
                }
            };
            onMounted(cb);
            onPatched(cb);
            onWillDestroy(() => {
                for (const result of observeRenderResults.values()) {
                    // owl could invoke onrendered and cancel immediately to re-render, so should compensate
                    if (result.has(this.constructor) && status(this) === "cancelled") {
                        result.set(this.constructor, result.get(this.constructor) - 1);
                    }
                }
            });
            return super.setup(...args);
        },
    });
    after(() => observeRenderResults.clear());
}

/**
 * This function tracks renders of components.
 * Should be prepared before mounting affected components with @see prepareObserveRenders
 * This function returns a function to stop observing, which itself returns
 * a Map of amount of renders per component. Key of map is Component constructor.
 *
 * @returns {() => Map<Component.constructor, number>}
 */
export function observeRenders() {
    const id = nextObserveRenderResults++;
    observeRenderResults.set(id, new Map());
    return () => {
        const result = observeRenderResults.get(id);
        observeRenderResults.delete(id);
        return result;
    };
}

/**
 * Determine if the child element is in the view port of the parent.
 *
 * @param {string} childSelector
 * @param {string} parentSelector
 */
export async function isInViewportOf(childSelector, parentSelector) {
    await contains(parentSelector);
    await contains(childSelector);
    const inViewportDeferred = new Deferred();
    const failTimeout = setTimeout(() => check({ crashOnFail: true }), 3000);
    const check = ({ crashOnFail = false } = {}) => {
        const parent = queryFirst(parentSelector);
        const child = queryFirst(childSelector);
        let alreadyInViewport = false;
        if (parent && child) {
            const childRect = child.getBoundingClientRect();
            const parentRect = parent.getBoundingClientRect();
            alreadyInViewport =
                childRect.top <= parentRect.top
                    ? parentRect.top - childRect.top <= childRect.height
                    : childRect.bottom - parentRect.bottom <= childRect.height;
        }
        if (alreadyInViewport) {
            clearTimeout(failTimeout);
            expect(true).toBe(true, {
                message: `Element ${childSelector} found in viewport of ${parentSelector}`,
            });
            inViewportDeferred.resolve();
        } else if (crashOnFail) {
            const failMsg = `Element ${childSelector} not found in viewport of ${parentSelector}`;
            expect(false).toBe(true, { message: failMsg });
            inViewportDeferred.reject(new Error(failMsg));
        } else {
            parent.addEventListener("scrollend", check, { once: true });
        }
    };
    check();
    return inViewportDeferred;
}

export async function hover(selector) {
    await contains(selector);
    await hootHover(selector);
}

function toChatHubData(opened, folded) {
    return JSON.stringify({
        opened: opened.map((data) => convertChatHubParam(data)),
        folded: folded.map((data) => convertChatHubParam(data)),
    });
}

function convertChatHubParam(param) {
    return typeof param === "number" ? { id: param, model: "discuss.channel" } : param;
}

export function setupChatHub({ opened = [], folded = [] } = {}) {
    browser.localStorage.setItem(CHAT_HUB_KEY, toChatHubData(opened, folded));
}

export function assertChatHub({ opened = [], folded = [] }) {
    expect(browser.localStorage.getItem(CHAT_HUB_KEY)).toEqual(toChatHubData(opened, folded));
}

export const STORE_FETCH_ROUTES = ["/mail/action", "/mail/data"];

/**
 * Prepares listeners for the various ways a store fetch could be triggered. It is important to call
 * this method before the RPC are done (typically before the start() of the test) to not miss any of
 * them. Each intercepted fetch should have a corresponding waitStoreFetch in the test.
 *
 * @param {string|string[]} [nameOrNames=[]] name or names of the store fetch params to intercept
 * (such as init_messaging or channels_as_member). If empty all params are intercepted.
 * @param {Object} [options={}]
 * @param {function} [options.onRpc] entry point to override the onRpc of the intercepted calls.
 * @param {string[]} [options.logParams=[]] names of the store fetch params for which both the name
 *  and the specific params should be logged in asyncStep. By default only the name is logged.
 */
export function listenStoreFetch(nameOrNames = [], { logParams = [], onRpc: onRpcOverride } = {}) {
    async function registerStep(request, name, params) {
        const res = await onRpcOverride?.(request);
        if (logParams.includes(name)) {
            asyncStep(`store fetch: ${name} - ${JSON.stringify(params)}`);
        } else {
            asyncStep(`store fetch: ${name}`);
        }
        return res;
    }
    async function registerSteps(request, fetchParams) {
        const namesToRegister = typeof nameOrNames === "string" ? [nameOrNames] : nameOrNames;
        let res;
        for (const fetchParam of fetchParams) {
            const name = typeof fetchParam === "string" ? fetchParam : fetchParam[0];
            const params = typeof fetchParam === "string" ? undefined : fetchParam[1];
            if (namesToRegister.length > 0) {
                if (namesToRegister.some((namesToRegister) => namesToRegister === name)) {
                    res = await registerStep(request, name, params);
                }
            } else {
                res = await registerStep(request, name, params);
            }
        }
        return res;
    }
    /**
     * The fetch could happen through any of those routes depending on various conditions.
     * Most tests don't care about which route is used, so we just listen to all of them.
     */
    onRpc("/mail/action", async (request) => {
        const { params } = await request.json();
        return registerSteps(request, params.fetch_params);
    });
    onRpc("/mail/data", async (request) => {
        const { params } = await request.json();
        return registerSteps(request, params.fetch_params);
    });
}

/**
 * Waits for the given name or names of store fetch parameters to have been fetched from the server,
 * in the given order. Expected names have to be registered with listenStoreFetch beforehand.
 * If other asyncStep are resolving in the same flow, they must be provided to stepsAfter (if they
 * are resolved after the fetch) or stepsBefore (if they are resolved before the fetch). The order
 * can be ignored with ignoreOrder option.
 *
 * @param {string|string[]} nameOrNames
 * @param {Object} [options={}]
 * @param {boolean} [options.ignoreOrder=false]
 * @param {string[]} [options.stepsAfter=[]]
 * @param {string[]} [options.stepsBefore=[]]
 */
export async function waitStoreFetch(
    nameOrNames = [],
    { ignoreOrder = false, stepsAfter = [], stepsBefore = [] } = {}
) {
    await waitForSteps(
        [
            ...stepsBefore,
            ...(typeof nameOrNames === "string" ? [nameOrNames] : nameOrNames).map(
                (nameOrNameAndParams) => {
                    if (typeof nameOrNameAndParams === "string") {
                        return `store fetch: ${nameOrNameAndParams}`;
                    }
                    return `store fetch: ${nameOrNameAndParams[0]} - ${JSON.stringify(
                        nameOrNameAndParams[1]
                    )}`;
                }
            ),
            ...stepsAfter,
        ],
        { ignoreOrder }
    );
    /**
     * Extra tick necessary to ensure the RPC is fully processed before resolving.
     * This is necessary because the asyncStep in onRpc is not synchronous with the moment
     * the RPC result is resolved and processed in the business code. Removing this tick
     * won't make everything fail, but it might create subtle race conditions.
     */
    await microTick();
}

export function userContext() {
    return { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] };
}

/**
 * @typedef VoiceMessagePatchResources
 * @property {AudioProcessor}
 */

/** @returns {VoiceMessagePatchResources} */
export function patchVoiceMessageAudio() {
    const res = { audioProcessor: undefined };
    const {
        AnalyserNode,
        AudioBufferSourceNode,
        AudioContext,
        AudioWorkletNode,
        GainNode,
        MediaStreamAudioSourceNode,
    } = browser;
    Object.assign(browser, {
        AnalyserNode: class {
            connect() {}
            disconnect() {}
        },
        AudioBufferSourceNode: class {
            buffer;
            constructor() {}
            connect() {}
            disconnect() {}
            start() {}
            stop() {}
        },
        AudioContext: class {
            audioWorklet;
            currentTime;
            destination;
            sampleRate;
            state;
            constructor() {
                this.audioWorklet = {
                    addModule(url) {},
                };
            }
            async close() {}
            /** @returns {AnalyserNode} */
            createAnalyser() {
                return new browser.AnalyserNode();
            }
            /** @returns {AudioBufferSourceNode} */
            createBufferSource() {
                return new browser.AudioBufferSourceNode();
            }
            /** @returns {GainNode} */
            createGain() {
                return new browser.GainNode();
            }
            /** @returns {MediaStreamAudioSourceNode} */
            createMediaStreamSource(microphone) {
                return new browser.MediaStreamAudioSourceNode();
            }
            /** @returns {AudioBuffer} */
            decodeAudioData(...args) {
                return new AudioContext().decodeAudioData(...args);
            }
        },
        AudioWorkletNode: class {
            port;
            constructor(audioContext, processorName) {
                this.port = {
                    onmessage(e) {},
                    postMessage(data) {
                        this.onmessage({ data, timeStamp: new Date().getTime() });
                    },
                };
                res.audioProcessor = this;
            }
            connect() {
                this.port.postMessage();
            }
            disconnect() {}
            process(allInputs) {
                const inputs = allInputs[0][0];
                this.port.postMessage(inputs);
                return true;
            }
        },
        GainNode: class {
            connect() {}
            close() {}
            disconnect() {}
        },
        MediaStreamAudioSourceNode: class {
            connect(processor) {}
            disconnect() {}
        },
    });
    after(() => {
        Object.assign(browser, {
            AnalyserNode,
            AudioBufferSourceNode,
            AudioContext,
            AudioWorkletNode,
            GainNode,
            MediaStreamAudioSourceNode,
        });
    });
    return res;
}

export function mockPermissionsPrompt() {
    patchWithCleanup(browser.navigator.permissions, {
        async query() {
            return {
                state: "prompt",
                addEventListener: () => {},
                removeEventListener: () => {},
                onchange: null,
            };
        },
    });
}

/**
 * Assert IM status on chat bubble and chat window of given `conversationName` with `count`.
 * The conversation should be present as a bubble initially, becomes open and folded again
 * after calling function.
 *
 * This is made as a function so that negative assertion on ImStatus can use this function and
 * ensure using correct selector and await properly like the positive assertions.
 *
 * @param {string} conversationName
 * @param {Number} count
 */
export async function assertChatBubbleAndWindowImStatus(conversationName, count) {
    await contains(`.o-mail-ChatBubble[name=${conversationName}]`);
    expect(`.o-mail-ChatBubble[name=${conversationName}] .o-mail-ImStatus`).toHaveCount(count);
    await click(`.o-mail-ChatBubble[name=${conversationName}]`);
    await contains(`.o-mail-ChatWindow-header:has(:text(${conversationName}))`);
    expect(
        `.o-mail-ChatWindow-header:has(:text(${conversationName})) .o-mail-ImStatus`
    ).toHaveCount(count);
    await click(`.o-mail-ChatWindow-header:has(:text(${conversationName}))`);
}
