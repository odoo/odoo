/** @odoo-module alias=@mail/../tests/helpers/webclient_setup default=false */

import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";

import { fileUploadService } from "@web/core/file_upload/file_upload_service";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { makeMockXHR, mocks, patchUserWithCleanup } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";

const ROUTES_TO_IGNORE = [
    "/web/webclient/load_menus",
    "/web/dataset/call_kw/res.users/load_views",
    "/hr_attendance/attendance_user_data",
];
const WEBCLIENT_PARAMETER_NAMES = new Set(["mockRPC", "serverData", "target", "webClientClass"]);
const SERVICES_PARAMETER_NAMES = new Set(["legacyServices", "services"]);

/**
 * @param {import("@web/core/registry").Registry} source
 * @param {import("@web/core/registry").Registry} target
 */
export function copyRegistry(source, target) {
    for (const [name, service] of source.getEntries()) {
        target.add(name, service);
    }
}

// Copy registries before they are cleared by the test setup in
// order to restore them during `getWebClientReady`.
const mailServicesRegistry = registry.category("mail.services");
const webServicesRegistry = registry.category("services");

const mailMainComponentsRegistry = registry.category("mail.main_components");
const webMainComponentsRegistry = registry.category("main_components");

const mailSystrayRegistry = registry.category("mail.systray");
const webSystrayRegistry = registry.category("systray");

QUnit.begin(() => {
    copyRegistry(webServicesRegistry, mailServicesRegistry);
    copyRegistry(webMainComponentsRegistry, mailMainComponentsRegistry);
    copyRegistry(webSystrayRegistry, mailSystrayRegistry);
});

/**
 * @returns function that returns an `XMLHttpRequest`-like object whose response
 * is computed by the given mock server.
 */
function getCreateXHR() {
    const mockedXHR = makeMockXHR();
    return function () {
        const xhr = mockedXHR();
        let response = "";
        let route = "";
        xhr.status = 200;
        patch(xhr, {
            open(method, dest) {
                route = dest;
                return super.open(method, dest);
            },
            async send(data) {
                await new Promise(setTimeout);
                response = JSON.stringify(await rpc(route, { body: data, method: "POST" }));
                return super.send(data);
            },
            upload: new EventTarget(),
            abort() {
                if (this._errorListener) {
                    this._errorListener();
                }
            },
            get response() {
                return response;
            },
        });
        return xhr;
    };
}

export const setupManager = {
    /**
     * Add required components to the main component registry.
     */
    setupMainComponentRegistry() {
        for (const [name, component] of mailMainComponentsRegistry.getEntries()) {
            webMainComponentsRegistry.add(name, component);
        }
        if (!registry.category("actions").contains("mail.action_discuss")) {
            registry.category("actions").add("mail.action_discuss", DiscussClientAction);
        }
    },
    /**
     * Add required components to the systray registry.
     */
    setupSystrayRegistry() {
        for (const [name, component] of mailSystrayRegistry.getEntries()) {
            if (!webSystrayRegistry.contains(name)) {
                webSystrayRegistry.add(name, component);
            }
        }
    },
    /**
     * Setup both legacy and new service registries.
     *
     * @param {Object} param0
     * @param {Object} [param0.services]
     * @param {Function} [param0.mockRPC]
     * @returns {LegacyRegistry} The registry containing all the legacy services that will be passed
     * to the webClient as a legacy parameter.
     */
    setupServiceRegistries({ services = {} } = {}) {
        const OriginalAudio = window.Audio;
        patchWithCleanup(window, {
            Audio: function () {
                const audio = new OriginalAudio();
                audio.preload = "none";
                audio.play = () => {};
                return audio;
            },
        });
        patchUserWithCleanup({ showEffect: true });
        if (!webServicesRegistry.contains("file_upload")) {
            webServicesRegistry.add("file_upload", {
                ...fileUploadService,
                start(env, ...args) {
                    this.env = env;
                    return fileUploadService.start.call(this, env, ...args);
                },
                createXhr: getCreateXHR(),
            });
        }
        for (const [name, service] of Object.entries(services)) {
            webServicesRegistry.add(name, service);
        }
        for (const [name, service] of mailServicesRegistry.getEntries()) {
            if (!mocks[name] && !name.includes("legacy_") && !webServicesRegistry.contains(name)) {
                webServicesRegistry.add(name, service);
            }
        }
    },
};

/**
 * Creates a properly configured instance of WebClient, with the messaging service and all it's
 * dependencies initialized.
 *
 * @param {Object} param0
 * @param {Object} [param0.serverData]
 * @param {Object} [param0.services]
 * @returns {WebClient}
 */
async function getWebClientReady(param0) {
    setupManager.setupMainComponentRegistry();

    const servicesParameters = {};
    const param0Entries = Object.entries(param0);
    for (const [parameterName, value] of param0Entries) {
        if (SERVICES_PARAMETER_NAMES.has(parameterName)) {
            servicesParameters[parameterName] = value;
        }
    }
    setupManager.setupServiceRegistries(servicesParameters);
    setupManager.setupSystrayRegistry();

    const webClientParameters = {};
    for (const [parameterName, value] of param0Entries) {
        if (WEBCLIENT_PARAMETER_NAMES.has(parameterName)) {
            webClientParameters[parameterName] = value;
        }
    }
    return createWebClient(webClientParameters);
}

export { getWebClientReady, ROUTES_TO_IGNORE };
