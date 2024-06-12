/* @odoo-module */

import { getPyEnv } from "@bus/../tests/helpers/mock_python_environment";
import { timings } from "@bus/misc";

import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { loadLamejs } from "@mail/discuss/voice_message/common/voice_message_service";
import { patchBrowserNotification } from "@mail/../tests/helpers/patch_notifications";
import { getAdvanceTime } from "@mail/../tests/helpers/time_control";
import { getWebClientReady } from "@mail/../tests/helpers/webclient_setup";

import { EventBus } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session as sessionInfo } from "@web/session";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import {
    clearRegistryWithCleanup,
    registryNamesToCloneWithCleanup,
    prepareRegistriesWithCleanup,
} from "@web/../tests/helpers/mock_env";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";

// load emoji data and lamejs once, when the test suite starts.
QUnit.begin(loadEmoji);
QUnit.begin(loadLamejs);
registryNamesToCloneWithCleanup.push("mock_server_callbacks", "discuss.model");

//------------------------------------------------------------------------------
// Public: test lifecycle
//------------------------------------------------------------------------------

function getOpenDiscuss(webClient, { context = {}, params = {}, ...props } = {}) {
    return async function openDiscuss(pActiveId) {
        const actionOpenDiscuss = {
            context: { ...context, active_id: pActiveId },
            id: "mail.action_discuss",
            params,
            tag: "mail.action_discuss",
            type: "ir.actions.client",
        };
        await doAction(webClient, actionOpenDiscuss, { props });
    };
}

function getOpenFormView(openView) {
    return async function openFormView(res_model, res_id, { props } = {}) {
        const action = {
            res_model,
            res_id,
            views: [[false, "form"]],
        };
        await openView(action, props);
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
    const categories = ["actions", "main_components", "services", "systray"];
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
export async function start(param0 = {}) {
    const { discuss = {}, hasTimeControl } = param0;
    patchWithCleanup(timings, {
        // make throttle instantaneous during tests
        throttle: (func) => func,
    });
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

    const pyEnv = await getPyEnv();
    patchWithCleanup(sessionInfo, {
        user_context: {
            ...sessionInfo.user_context,
            uid: pyEnv.currentUserId,
        },
        uid: pyEnv.currentUserId,
        name: pyEnv.currentUser?.name,
        partner_id: pyEnv.currentPartnerId,
    });
    if (browser.Notification && !browser.Notification.isPatched) {
        patchBrowserNotification("denied");
    }
    param0.serverData = param0.serverData || getActionManagerServerData();
    param0.serverData.models = { ...pyEnv.getData(), ...param0.serverData.models };
    param0.serverData.views = { ...pyEnv.getViews(), ...param0.serverData.views };
    const webClient = await getWebClientReady({ ...param0, messagingBus });
    if (webClient.env.services.ui.isSmall) {
        target.style.width = "100%";
    }
    const openView = async (action, options) => {
        action["type"] = action["type"] || "ir.actions.act_window";
        await doAction(webClient, action, { props: options });
    };
    return {
        advanceTime,
        env: webClient.env,
        openDiscuss: getOpenDiscuss(webClient, discuss),
        openView,
        openFormView: getOpenFormView(openView),
        pyEnv,
        target,
        webClient,
    };
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
