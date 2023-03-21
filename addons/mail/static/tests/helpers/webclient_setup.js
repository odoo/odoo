/* @odoo-module */

import { busParametersService } from "@bus/bus_parameters_service";
import { imStatusService } from "@bus/im_status_service";
import { multiTabService } from "@bus/multi_tab_service";
import { busService } from "@bus/services/bus_service";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";

import { attachmentService } from "@mail/core/common/attachment_service";
import { channelMemberService } from "@mail/core/common/channel_member_service";
import { ChatWindowContainer } from "@mail/core/common/chat_window_container";
import { chatWindowService } from "@mail/core/common/chat_window_service";
import { messageService } from "@mail/core/common/message_service";
import { messagingService } from "@mail/core/common/messaging_service";
import { notificationPermissionService } from "@mail/core/common/notification_permission_service";
import { outOfFocusService } from "@mail/core/common/out_of_focus_service";
import { personaService } from "@mail/core/common/persona_service";
import { soundEffects } from "@mail/core/common/sound_effects_service";
import { storeService } from "@mail/core/common/store_service";
import { suggestionService } from "@mail/core/common/suggestion_service";
import { threadService } from "@mail/core/common/thread_service";
import { userSettingsService } from "@mail/core/common/user_settings_service";
import { ActivityMenu } from "@mail/core/web/activity_menu";
import { activityService } from "@mail/core/web/activity_service";
import { DiscussClientAction } from "@mail/core/web/discuss_client_action";
import { MessagingMenu } from "@mail/core/web/messaging_menu";

import { effectService } from "@web/core/effects/effect_service";
import { fileUploadService } from "@web/core/file_upload/file_upload_service";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { makeMockXHR } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { gifPickerService } from "@mail/discuss/gif_picker/common/gif_picker_service";

const ROUTES_TO_IGNORE = [
    "/web/webclient/load_menus",
    "/web/dataset/call_kw/res.users/load_views",
    "/web/dataset/call_kw/res.users/systray_get_activities",
];
const WEBCLIENT_PARAMETER_NAMES = new Set([
    "legacyParams",
    "mockRPC",
    "serverData",
    "target",
    "webClientClass",
]);
const SERVICES_PARAMETER_NAMES = new Set([
    "legacyServices",
    "loadingBaseDelayDuration",
    "messagingBus",
    "services",
]);

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
        const self = this;
        xhr.status = 200;
        patch(xhr, "mail", {
            open(method, dest) {
                route = dest;
                return this._super(method, dest);
            },
            async send(data) {
                const _super = this._super;
                await new Promise(setTimeout);
                response = JSON.stringify(
                    await self.env.services.rpc(route, { body: data, method: "POST" })
                );
                return _super(data);
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
        const mainComponentRegistry = registry.category("main_components");
        mainComponentRegistry.add("mail.ChatWindowContainer", {
            Component: ChatWindowContainer,
        });
        if (!registry.category("actions").contains("mail.action_discuss")) {
            registry.category("actions").add("mail.action_discuss", DiscussClientAction);
        }
    },
    /**
     * Setup both legacy and new service registries.
     *
     * @param {Object} param0
     * @param {Object} [param0.services]
     * @param {number} [param0.loadingBaseDelayDuration=0]
     * @param {EventBus} [param0.messagingBus]
     * @param {Function} [param0.mockRPC]
     * @returns {LegacyRegistry} The registry containing all the legacy services that will be passed
     * to the webClient as a legacy parameter.
     */
    async setupMessagingServiceRegistries({
        loadingBaseDelayDuration = 0,
        messagingBus,
        services,
    } = {}) {
        const serviceRegistry = registry.category("services");

        const OriginalAudio = window.Audio;
        patchWithCleanup(
            window,
            {
                Audio: function () {
                    const audio = new OriginalAudio();
                    audio.preload = "none";
                    audio.play = () => {};
                    return audio;
                },
            },
            { pure: true }
        );

        const messagingValues = {
            start() {
                return {
                    isInQUnitTest: true,
                    disableAnimation: true,
                    loadingBaseDelayDuration,
                    messagingBus,
                    userNotificationManager: { canPlayAudio: false },
                };
            },
        };

        services = setupManager.setupServices(services, messagingValues);
        if (!serviceRegistry.contains("file_upload")) {
            serviceRegistry.add("file_upload", {
                ...fileUploadService,
                start(env, ...args) {
                    this.env = env;
                    return fileUploadService.start.call(this, env, ...args);
                },
                createXhr: getCreateXHR(),
            });
        }
        patchWithCleanup(session, { show_effect: true });
        Object.entries(services).forEach(([serviceName, service]) => {
            if (!serviceRegistry.contains(serviceName)) {
                serviceRegistry.add(serviceName, service);
            }
        });
        registry
            .category("systray")
            .add("mail.activity_menu", { Component: ActivityMenu }, { sequence: 20 });
        registry
            .category("systray")
            .add("mail.messaging_menu", { Component: MessagingMenu }, { sequence: 25 });
    },
    setupServices(services, messagingValues) {
        return {
            bus_service: busService,
            "bus.parameters": busParametersService,
            im_status: imStatusService,
            effect: effectService,
            "discuss.channel.member": channelMemberService,
            "discuss.gifPicker": gifPickerService,
            "mail.notification.permission": notificationPermissionService,
            "mail.suggestion": suggestionService,
            "mail.store": storeService,
            "mail.activity": activityService,
            "mail.attachment": attachmentService,
            "mail.thread": threadService,
            "mail.message": messageService,
            "mail.chat_window": chatWindowService,
            "mail.messaging": messagingService,
            "mail.sound_effects": soundEffects,
            "mail.user_settings": userSettingsService,
            "mail.persona": personaService,
            "mail.out_of_focus": outOfFocusService,
            messagingValues,
            presence: makeFakePresenceService({
                isOdooFocused: () => true,
            }),
            multi_tab: multiTabService,
            ...services,
        };
    },
};

/**
 * Creates a properly configured instance of WebClient, with the messaging service and all it's
 * dependencies initialized.
 *
 * @param {Object} param0
 * @param {Object} [param0.serverData]
 * @param {Object} [param0.services]
 * @param {Object} [param0.loadingBaseDelayDuration]
 * @param {EventBus} [param0.messagingBus] The event bus to be used by messaging.
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
    await setupManager.setupMessagingServiceRegistries(servicesParameters);

    const webClientParameters = {};
    for (const [parameterName, value] of param0Entries) {
        if (WEBCLIENT_PARAMETER_NAMES.has(parameterName)) {
            webClientParameters[parameterName] = value;
        }
    }
    return createWebClient(webClientParameters);
}

export { getWebClientReady, ROUTES_TO_IGNORE };
