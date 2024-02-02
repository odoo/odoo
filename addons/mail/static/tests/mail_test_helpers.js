/** @odoo-module */

import { MEDIAS_BREAKPOINTS, utils as uiUtils } from "@web/core/ui/ui_service";
export { SIZES } from "@web/core/ui/ui_service";
export * from "./mail_test_helpers_contains";
import { busModels } from "@bus/../tests/bus_test_helpers";
import {
    MockServer,
    defineModels,
    makeMockServer,
    mountView,
    mountWithCleanup,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
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
import { MailActivityType } from "./mock_server/mock_models/mail_activity_type";
import { MailFollowers } from "./mock_server/mock_models/mail_followers";
import { MailGuest } from "./mock_server/mock_models/mail_guest";
import { MailLinkPreview } from "./mock_server/mock_models/mail_link_preview";
import { MailMessage } from "./mock_server/mock_models/mail_message";
import { MailMessageReaction } from "./mock_server/mock_models/mail_message_reaction";
import { MailMessageSubtype } from "./mock_server/mock_models/mail_message_subtype";
import { MailNotification } from "./mock_server/mock_models/mail_notification";
import { MailShortcode } from "./mock_server/mock_models/mail_shortcode";
import { MailTemplate } from "./mock_server/mock_models/mail_template";
import { MailThread } from "./mock_server/mock_models/mail_thread";
import { MailTrackingValue } from "./mock_server/mock_models/mail_tracking_value";
import { ResFake } from "./mock_server/mock_models/res_fake";
import { ResPartner } from "./mock_server/mock_models/res_partner";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { ResUsersSettings } from "./mock_server/mock_models/res_users_settings";
import { ResUsersSettingsVolumes } from "./mock_server/mock_models/res_users_settings_volumes";
import { WebClient } from "@web/webclient/webclient";
import { browser } from "@web/core/browser/browser";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { tick } from "@odoo/hoot-mock";
import { after, before, beforeAll } from "@odoo/hoot";
import { isMacOS } from "@web/core/browser/feature_detection";
import { triggerEvents } from "./mail_test_helpers_contains";
import { DISCUSS_ACTION_ID } from "./mock_server/mail_mock_server";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { loadLamejs } from "@mail/discuss/voice_message/common/voice_message_service";
import { registry } from "@web/core/registry";

// load emoji data and lamejs once, when the test suite starts.
beforeAll(loadEmoji, loadLamejs);
before(prepareRegistriesWithCleanup);
export const registryNamesToCloneWithCleanup = [];
registryNamesToCloneWithCleanup.push("mock_server_callbacks", "discuss.model");

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function defineMailModels() {
    return defineModels({ ...webModels, ...busModels, ...mailModels });
}

export const mailModels = {
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
    MailActivityType,
    MailFollowers,
    MailGuest,
    MailLinkPreview,
    MailMessage,
    MailMessageReaction,
    MailMessageSubtype,
    MailNotification,
    MailShortcode,
    MailTemplate,
    MailThread,
    MailTrackingValue,
    ResFake,
    ResPartner,
    ResUsers,
    ResUsersSettings,
    ResUsersSettingsVolumes,
};

function mockTimeout() {
    const timeouts = new Map();
    let currentTime = 0;
    let id = 1;
    patchWithCleanup(browser, {
        setTimeout(fn, delay = 0) {
            timeouts.set(id, { fn, scheduledFor: delay + currentTime, id });
            return id++;
        },
        clearTimeout(id) {
            timeouts.delete(id);
        },
    });
    return {
        execRegisteredTimeouts() {
            for (const { fn } of timeouts.values()) {
                fn();
            }
            timeouts.clear();
        },
        async advanceTime(duration) {
            // wait here so all microtasktick scheduled in this frame can be
            // executed and possibly register their own timeout
            await tick();
            currentTime += duration;
            for (const { fn, scheduledFor, id } of timeouts.values()) {
                if (scheduledFor <= currentTime) {
                    fn();
                    timeouts.delete(id);
                }
            }
            // wait here to make sure owl can update the UI
            await tick();
        },
    };
}

let archs = {};
export function registerArchs(newArchs) {
    archs = newArchs;
    after(() => (archs = {}));
}

export async function openDiscuss(activeId, { context = {}, params = {}, ...props } = {}) {
    const env = getMockEnv();
    await env.services.action.doAction(
        {
            context: { ...context, active_id: activeId },
            id: DISCUSS_ACTION_ID,
            params,
            tag: "mail.action_discuss",
            type: "ir.actions.client",
        },
        { props }
    );
    // await mountWithCleanup(DiscussClientAction, { props: { action: {  } context.active_id } });
}

export async function openFormView(resModel, resId, params) {
    return openView({
        res_model: resModel,
        res_id: resId,
        views: [[false, "form"]],
        view_mode: "form",
        ...params,
    });
}

export async function openKanbanView(resModel, params) {
    return openView({
        res_model: resModel,
        views: [[false, "kanban"]],
        view_mode: "kanban",
        ...params,
    });
}

export async function openListView(resModel, params) {
    return openView({
        res_model: resModel,
        views: [[false, "list"]],
        view_mode: "list",
        ...params,
    });
}

export async function openView({ res_model, res_id, views, ...params }) {
    const [[, type]] = views;
    await mountView({
        type,
        resModel: res_model,
        resId: res_id,
        arch: params?.arch || archs[res_model + ",false," + type] || undefined,
        ...params,
    });
}

export async function start({
    hasTimeControl = false,
    serverData,
    asTab = false,
    services,
    session,
} = {}) {
    if (!MockServer.current) {
        await startServer();
    }
    await mountWithCleanup(WebClient);
    const env = getMockEnv();
    return {
        advanceTime: hasTimeControl ? mockTimeout().advanceTime : undefined,
        env,
        pyEnv: MockServer.current.env,
    };
}

export async function startServer() {
    const { env } = await makeMockServer();
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
export function patchUiSize({ height, size, width }) {
    if ((!size && !width) || (size && width)) {
        throw new Error("Either size or width must be given to the patchUiSize function");
    }
    size = size === undefined ? getSizeFromWidth(width) : size;
    width = width || getWidthFromSize(size);

    patchWithCleanup(browser, {
        innerWidth: width,
        innerHeight: height || browser.innerHeight,
    });
    patchWithCleanup(uiUtils, {
        getSize() {
            return size;
        },
    });
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

/**
 * Triggers an hotkey properly disregarding the operating system.
 *
 * @param {string} hotkey
 * @param {boolean} addOverlayModParts
 * @param {KeyboardEventInit} eventAttrs
 */
export async function triggerHotkey(hotkey, addOverlayModParts = false, eventAttrs = {}) {
    eventAttrs.key = hotkey.split("+").pop();

    if (/shift/i.test(hotkey)) {
        eventAttrs.shiftKey = true;
    }

    if (/control/i.test(hotkey)) {
        if (isMacOS()) {
            eventAttrs.metaKey = true;
        } else {
            eventAttrs.ctrlKey = true;
        }
    }

    if (/alt/i.test(hotkey) || addOverlayModParts) {
        if (isMacOS()) {
            eventAttrs.ctrlKey = true;
        } else {
            eventAttrs.altKey = true;
        }
    }

    if (!("bubbles" in eventAttrs)) {
        eventAttrs.bubbles = true;
    }

    const [keydownEvent, keyupEvent] = await triggerEvents(
        document.activeElement,
        null,
        [
            ["keydown", eventAttrs],
            ["keyup", eventAttrs],
        ],
        { skipVisibilityCheck: true }
    );

    return { keydownEvent, keyupEvent };
}

export function clearRegistryWithCleanup(registry) {
    prepareRegistry(registry);
}

function cloneRegistryWithCleanup(registry) {
    prepareRegistry(registry, true);
}

function prepareRegistry(registry, keepContent = false) {
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
