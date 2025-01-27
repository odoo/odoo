import { busModels } from "@bus/../tests/bus_test_helpers";
import { after, before, expect, getFixture, registerDebugInfo } from "@odoo/hoot";
import { hover as hootHover, queryFirst, resize } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
import {
    MockServer,
    authenticate,
    defineModels,
    defineParams,
    getMockEnv,
    getService,
    makeMockEnv,
    makeMockServer,
    mountWithCleanup,
    parseViewProps,
    patchWithCleanup,
    restoreRegistry,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";
import { contains } from "./mail_test_helpers_contains";

import { busService } from "@bus/services/bus_service";
import { mailGlobal } from "@mail/utils/common/misc";
import { Component, onMounted, onPatched, onWillDestroy, status } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { MEDIAS_BREAKPOINTS, utils as uiUtils } from "@web/core/ui/ui_service";
import { useServiceProtectMethodHandling } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { WebClient } from "@web/webclient/webclient";
export { SIZES } from "@web/core/ui/ui_service";

import {
    DISCUSS_ACTION_ID,
    authenticateGuest,
    mailDataHelpers,
} from "./mock_server/mail_mock_server";
import { Base } from "./mock_server/mock_models/base";
import { DEFAULT_MAIL_VIEW_ID } from "./mock_server/mock_models/constants";
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
import { MailMessageReaction } from "./mock_server/mock_models/mail_message_reaction";
import { MailMessageSubtype } from "./mock_server/mock_models/mail_message_subtype";
import { MailNotification } from "./mock_server/mock_models/mail_notification";
import { MailPushDevice } from "./mock_server/mock_models/mail_push_device";
import { MailScheduledMessage } from "./mock_server/mock_models/mail_scheduled_message";
import { MailTemplate } from "./mock_server/mock_models/mail_template";
import { MailThread } from "./mock_server/mock_models/mail_thread";
import { MailTrackingValue } from "./mock_server/mock_models/mail_tracking_value";
import { ResFake } from "./mock_server/mock_models/res_fake";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { ResUsersSettings } from "./mock_server/mock_models/res_users_settings";
import { ResUsersSettingsVolumes } from "./mock_server/mock_models/res_users_settings_volumes";

export * from "./mail_test_helpers_contains";

before(prepareRegistriesWithCleanup);
export const registryNamesToCloneWithCleanup = [];
registryNamesToCloneWithCleanup.push("mock_server_callbacks", "discuss.model");

mailGlobal.isInTest = true;
useServiceProtectMethodHandling.fn = useServiceProtectMethodHandling.mocked; // so that RPCs after tests do not throw error

patch(busService, {
    _onMessage(id, type, payload) {
        super._onMessage(...arguments);
        if (type === "mail.record/insert") {
            const recordsByModelName = Object.entries(payload);
            for (const [modelName, records] of recordsByModelName) {
                for (const record of Array.isArray(records) ? records : [records]) {
                    registerDebugInfo(modelName, record);
                }
            }
        }
    },
});
//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function defineMailModels() {
    defineParams({ suite: "mail" }, "replace");
    return defineModels(mailModels);
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
    MailMessageReaction,
    MailMessageSubtype,
    MailNotification,
    MailPushDevice,
    MailScheduledMessage,
    MailTemplate,
    MailThread,
    MailTrackingValue,
    ResFake,
    ResPartner,
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
        const handler = registry.category("mock_rpc").get(route);
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
    const handler = registry.category("mock_rpc").get(route);
    patchWithCleanup(handler, { after: callback });
}

let archs = {};
export function registerArchs(newArchs) {
    archs = newArchs;
    after(() => (archs = {}));
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
        views: [[getMailViewId(resModel, "form") || false, "form"]],
        ...params,
    });
}

export async function openKanbanView(resModel, params) {
    return openView({
        res_model: resModel,
        views: [[getMailViewId(resModel, "kanban"), "kanban"]],
        ...params,
    });
}

export async function openListView(resModel, params) {
    return openView({
        res_model: resModel,
        views: [[getMailViewId(resModel, "list"), "list"]],
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
        arch:
            params?.arch ||
            archs[viewId || res_model + `,${getMailViewId(res_model, type) || false},` + type] ||
            undefined,
        viewId: params?.arch || viewId,
        ...params,
    });
    await getService("action").doAction(action, { props: options });
}
/** @type {import("@web/../tests/_framework/mock_server/mock_server").MockServerEnvironment} */
let pyEnv;
function getMailViewId(res_model, type) {
    const prefix = `${type},${DEFAULT_MAIL_VIEW_ID}`;
    if (pyEnv[res_model]._views[prefix]) {
        return DEFAULT_MAIL_VIEW_ID;
    }
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

/**
 * @param {{
 *  asTab?: boolean;
 *  authenticateAs?: any | { login: string; password: string; };
 *  env?: Partial<OdooEnv>;
 * }} [options]
 */
export async function start(options) {
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
        restoreRegistry(registry);
        const rootTarget = target;
        target = document.createElement("div");
        target.style.width = "100%";
        rootTarget.appendChild(target);
        addSwitchTabDropdownItem(rootTarget, target);
        env = await makeMockEnv({}, { makeNew: true });
    } else {
        env = getMockEnv() || (await makeMockEnv({}));
    }
    env.testEnv = true;
    await mountWithCleanup(WebClient, { env, target });
    return Object.assign(env, { ...options?.env, target });
}

export async function startServer() {
    const { env } = await makeMockServer();
    pyEnv = env;
    pyEnv["res.users"].write([serverState.userId], {
        groups_id: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupId]])
            .map(({ id }) => id),
    });
    return env;
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
        clone() {
            return Object.assign(new MockMediaStreamTrack(this.kind), { ...this });
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
    after(() => {
        // stop all streams as some tests may not do actions that lead to the ending of tracks
        streams.forEach((stream) => {
            stream.getTracks().forEach((track) => track.stop());
        });
    });
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
