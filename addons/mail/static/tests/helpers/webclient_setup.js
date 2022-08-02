/** @odoo-module **/

import { busService } from '@bus/services/bus_service';
import { multiTabService } from '@bus/multi_tab_service';
import { makeBusServiceToLegacyEnv } from '@bus/services/legacy/make_bus_service_to_legacy_env';
import { makeMultiTabToLegacyEnv } from '@bus/services/legacy/make_multi_tab_to_legacy_env';
import { makeFakePresenceService } from '@bus/../tests/helpers/mock_services';

import { ChatWindowManagerContainer } from '@mail/components/chat_window_manager_container/chat_window_manager_container';
import { DialogManagerContainer } from '@mail/components/dialog_manager_container/dialog_manager_container';
import { DiscussContainer } from '@mail/components/discuss_container/discuss_container';
import { PopoverManagerContainer } from '@mail/components/popover_manager_container/popover_manager_container';
import { messagingService } from '@mail/services/messaging_service';
import { systrayService } from '@mail/services/systray_service';
import { makeMessagingToLegacyEnv } from '@mail/utils/make_messaging_to_legacy_env';

import { registry } from '@web/core/registry';
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";

const ROUTES_TO_IGNORE = [
    '/longpolling/poll',
    '/web/webclient/load_menus',
    '/web/dataset/call_kw/res.users/load_views',
    '/web/dataset/call_kw/res.users/systray_get_activities'
];
const WEBCLIENT_PARAMETER_NAMES = new Set(['legacyParams', 'mockRPC', 'serverData', 'target', 'webClientClass']);
const SERVICES_PARAMETER_NAMES = new Set([
    'legacyServices', 'loadingBaseDelayDuration', 'messagingBeforeCreationDeferred',
    'messagingBus', 'services', 'testSetupDoneDeferred',
]);

/**
 * Add required components to the main component registry.
 */
 function setupMainComponentRegistry() {
    const mainComponentRegistry = registry.category('main_components');
    mainComponentRegistry.add('ChatWindowManagerContainer', { Component: ChatWindowManagerContainer });
    mainComponentRegistry.add('DialogManagerContainer', { Component: DialogManagerContainer });
    registry.category('actions').add('mail.action_discuss', DiscussContainer);
    mainComponentRegistry.add('PopoverManagerContainer', { Component: PopoverManagerContainer });
}

/**
 * Setup both legacy and new service registries.
 *
 * @param {Object} param0
 * @param {Object} [param0.services]
 * @param {number} [param0.loadingBaseDelayDuration=0]
 * @param {Promise} [param0.messagingBeforeCreationDeferred=Promise.resolve()]
 *   Deferred that let tests block messaging creation and simulate resolution.
 *   Useful for testing components behavior when messaging is not yet created.
 * @param {EventBus} [param0.messagingBus]
 * @param {Promise} [param0.testSetupDoneDeferred] The Promise to whose revolution has to be
 * waited before starting the messaging service.
 * @returns {LegacyRegistry} The registry containing all the legacy services that will be passed
 * to the webClient as a legacy parameter.
 */
function setupMessagingServiceRegistries({
    loadingBaseDelayDuration = 0,
    messagingBeforeCreationDeferred = Promise.resolve(),
    messagingBus,
    services,
    testSetupDoneDeferred,
 }) {
    const serviceRegistry = registry.category('services');

    patchWithCleanup(messagingService, {
        async _startModelManager() {
            const _super = this._super.bind(this);
            await testSetupDoneDeferred;
            await messagingBeforeCreationDeferred;
            return _super(...arguments);
        },
    });

    const messagingValues = {
        start() {
            return {
                isInQUnitTest: true,
                disableAnimation: true,
                loadingBaseDelayDuration,
                messagingBus,
            };
        }
    };

    const customBusService = {
        ...busService,
        start() {
            const originalService = busService.start(...arguments);
            Object.assign(originalService, {
                _beep() {}, // Do nothing
                _registerWindowUnload() {}, // Do nothing
                updateOption() {},
            });
            return originalService;
        },
    };

    services = {
        bus_service: customBusService,
        messaging: messagingService,
        messagingValues,
        presence: makeFakePresenceService({
            isOdooFocused: () => true,
        }),
        systrayService,
        multi_tab: multiTabService,
        ...services,
    };

    Object.entries(services).forEach(([serviceName, service]) => {
        serviceRegistry.add(serviceName, service);
    });

    registry.category('wowlToLegacyServiceMappers').add('bus_service_to_legacy_env', makeBusServiceToLegacyEnv);
    registry.category('wowlToLegacyServiceMappers').add('multi_tab_to_legacy_env', makeMultiTabToLegacyEnv);
    registry.category('wowlToLegacyServiceMappers').add('messaging_service_to_legacy_env', makeMessagingToLegacyEnv);
}

/**
 * Creates a properly configured instance of WebClient, with the messaging service and all it's
 * dependencies initialized.
 *
 * @param {Object} param0
 * @param {Object} [param0.serverData]
 * @param {Object} [param0.services]
 * @param {Object} [param0.loadingBaseDelayDuration]
 * @param {Object} [param0.messagingBeforeCreationDeferred]
 * @param {Promise} [param0.testSetupDoneDeferred] The Promise to whose revolution has to be
 * waited before starting the messaging service.
 * @param {EventBus} [param0.messagingBus] The event bus to be used by messaging.
 * @returns {WebClient}
 */
 async function getWebClientReady(param0) {
    setupMainComponentRegistry();

    const servicesParameters = {};
    const param0Entries = Object.entries(param0);
    for (const [parameterName, value] of param0Entries) {
        if (SERVICES_PARAMETER_NAMES.has(parameterName)) {
            servicesParameters[parameterName] = value;
        }
    }
    setupMessagingServiceRegistries(servicesParameters);

    const webClientParameters = {};
    for (const [parameterName, value] of param0Entries) {
        if (WEBCLIENT_PARAMETER_NAMES.has(parameterName)) {
            webClientParameters[parameterName] = value;
        }
    }
    return createWebClient(webClientParameters);
}

export {
    getWebClientReady,
    ROUTES_TO_IGNORE,
};
