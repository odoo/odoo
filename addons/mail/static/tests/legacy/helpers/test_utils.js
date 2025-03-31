/** @odoo-module alias=@mail/../tests/helpers/test_utils default=false */

import { getPyEnv } from "@bus/../tests/helpers/mock_python_environment";
import { timings } from "@bus/misc";

import { loadLamejs } from "@mail/discuss/voice_message/common/voice_message_service";
import { patchBrowserNotification } from "@mail/../tests/helpers/patch_notifications";
import { getAdvanceTime } from "@mail/../tests/helpers/time_control";
import { getWebClientReady } from "@mail/../tests/helpers/webclient_setup";

import { browser } from "@web/core/browser/browser";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import {
    clearRegistryWithCleanup,
    registryNamesToCloneWithCleanup,
    prepareRegistriesWithCleanup,
} from "@web/../tests/helpers/mock_env";
import { patchUserWithCleanup } from "@web/../tests/helpers/mock_services";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { DISCUSS_ACTION_ID } from "./test_constants";

// load emoji data and lamejs once, when the test suite starts.
QUnit.begin(loadEmoji);
QUnit.begin(loadLamejs);
registryNamesToCloneWithCleanup.push("mock_server_callbacks", "discuss.model");

//------------------------------------------------------------------------------
// Public: test lifecycle
//------------------------------------------------------------------------------

let currentEnv = null;

export async function openDiscuss(activeId, { target } = {}) {
    const env = target ?? currentEnv;
    await env.services.action.doAction({
        context: { active_id: activeId },
        id: DISCUSS_ACTION_ID,
        tag: "mail.action_discuss",
        type: "ir.actions.client",
    });
}

export async function openFormView(resModel, resId, { props = {}, target } = {}) {
    const env = target ?? currentEnv;
    await env.services.action.doAction(
        {
            res_model: resModel,
            res_id: resId,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        },
        { props }
    );
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
    const onClickDropdownItem = (e) => {
        const dropdownToggle = dropdownDiv.querySelector(".dropdown-toggle");
        dropdownToggle.innerText = `Switch Tab (${e.target.innerText})`;
        tabs.forEach((tab) => (tab.style.zIndex = -zIndexMainTab));
        if (e.target.innerText !== "Qunit") {
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
                <li><a class="dropdown-item">Qunit</a></li>
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
 * Main function used to make a mocked environment with mocked messaging env.
 *
 * @param {Object} [param0={}]
 * @param {boolean} [param0.asTab] Whether or not the resulting WebClient should
 * be considered as a separate tab.
 * @param {Object} [param0.serverData] The data to pass to the webClient
 * @param {Object} [param0.legacyServices]
 * @param {Object} [param0.services]
 * @param {function} [param0.mockRPC]
 * @param {boolean} [param0.hasTimeControl=false] if set, all flow of time with
 *   `messaging.browser.setTimeout` are fully controlled by test itself.
 * @returns {Object}
 */
export async function start(param0 = {}) {
    const { hasTimeControl } = param0;
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
    const pyEnv = await getPyEnv();
    patchWithCleanup(session, {
        storeData: pyEnv.mockServer._mockResUsers__init_store_data(),
    });
    if (!pyEnv.currentUser._is_public()) {
        const userSettings = pyEnv.mockServer._mockResUsersSettings_FindOrCreateForUser(
            pyEnv.currentUser.id
        );
        const settings = pyEnv.mockServer._mockResUsersSettings_ResUsersSettingsFormat(
            userSettings.id
        );
        patchUserWithCleanup({ settings });
    }
    if (browser.Notification && !browser.Notification.isPatched) {
        patchBrowserNotification("denied");
    }
    param0.serverData = param0.serverData || getActionManagerServerData();
    param0.serverData.models = { ...pyEnv.getData(), ...param0.serverData.models };
    param0.serverData.views = { ...pyEnv.getViews(), ...param0.serverData.views };
    const webClient = await getWebClientReady({ ...param0 });
    if (webClient.env.services.ui.isSmall) {
        target.style.width = "100%";
    }
    const openView = async (action, options) => {
        action["type"] = action["type"] || "ir.actions.act_window";
        await doAction(webClient, action, { props: options });
    };
    currentEnv = webClient.env;
    registerCleanup(() => (currentEnv = undefined));
    return {
        advanceTime,
        env: webClient.env,
        openDiscuss: (activeId) => openDiscuss(activeId, { target: webClient.env }),
        openView,
        openFormView: (resModel, resId) => openFormView(resModel, resId, { target: webClient.env }),
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
