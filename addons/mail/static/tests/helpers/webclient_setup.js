/** @odoo-module **/

import { legacyBusService } from '@bus/js/services/legacy/legacy_bus_service';

import BusService from 'bus.BusService';

import { ChatWindowManagerContainer } from '@mail/components/chat_window_manager_container/chat_window_manager_container';
import { DialogManagerContainer } from '@mail/components/dialog_manager_container/dialog_manager_container';
import { DiscussContainer } from '@mail/components/discuss_container/discuss_container';
import { messagingService } from '@mail/services/messaging_service';
import { makeMessagingToLegacyEnv } from '@mail/utils/make_messaging_to_legacy_env';

import { registry } from '@web/core/registry';
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";

import AbstractStorageService from 'web.AbstractStorageService';
import RamStorage from 'web.RamStorage';
import LegacyRegistry from 'web.Registry';

const WEBCLIENT_LOAD_ROUTES = [
    '/web/webclient/load_menus',
    '/web/dataset/call_kw/res.users/load_views',
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
}

/**
 * Setup both legacy and new service registries.
 *
 * @param {Object} param0
 * @param {Object} [param0.services]
 * @param {Object} [param0.legacyServices]
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
    legacyServices,
    loadingBaseDelayDuration = 0,
    messagingBeforeCreationDeferred = Promise.resolve(),
    messagingBus,
    services,
    testSetupDoneDeferred,
 }) {
    const serviceRegistry = registry.category('services');
    const legacyServiceRegistry = new LegacyRegistry();
    legacyServices = {
        bus_service: BusService.extend({
            _beep() {}, // Do nothing
            _poll() {}, // Do nothing
            _registerWindowUnload() {}, // Do nothing
            isOdooFocused() {
                return true;
            },
            updateOption() {},
        }),
        local_storage: AbstractStorageService.extend({ storage: new RamStorage() }),
        ...legacyServices,
    };

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
                autofetchPartnerImStatus: false,
                disableAnimation: true,
                loadingBaseDelayDuration,
                messagingBus,
            };
        }
    };

    services = {
        messagingValues,
        ...services,
    };
    // during tests, we need to wait for the legacyBusService to be added  before adding the messaging
    // service to the registry or it will result in an error during the webClient creation.
    const addMessagingToRegistryFn = ev => {
        const { key, operation } = ev.detail;
        if (key === 'legacy_bus_service' && operation === 'add') {
            serviceRegistry.add('messaging', messagingService);
            serviceRegistry.add('messaging_service_to_legacy_env', makeMessagingToLegacyEnv(owl.Component.env));
            serviceRegistry.removeEventListener('UPDATE', addMessagingToRegistryFn);
        }
    };
    serviceRegistry.addEventListener('UPDATE', addMessagingToRegistryFn);

    Object.entries(services).forEach(([serviceName, service]) => {
        serviceRegistry.add(serviceName, service);
    });
    Object.entries(legacyServices).forEach(([serviceName, service]) => {
        legacyServiceRegistry.add(serviceName, service);
    });

    return legacyServiceRegistry;
}

/**
 * Creates a properly configured instance of WebClient, with the messaging service and all it's
 * dependencies initialized.
 *
 * @param {Object} param0
 * @param {Object} [param0.serverData]
 * @param {Object} [param0.services]
 * @param {Object} [param0.legacyServices]
 * @param {Object} [param0.legacyParams={}]
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
    const legacyServiceRegistry = setupMessagingServiceRegistries(servicesParameters);

    const webClientParameters = {};
    for (const [parameterName, value] of param0Entries) {
        if (WEBCLIENT_PARAMETER_NAMES.has(parameterName)) {
            webClientParameters[parameterName] = value;
        }
    }
    webClientParameters.legacyParams = {
        legacyServicesToDeployInWowlEnv: {
            legacy_bus_service: legacyBusService,
        },
        serviceRegistry: legacyServiceRegistry,
        ...webClientParameters.legacyParams,
    };
    return createWebClient(webClientParameters);
}

export {
    getWebClientReady,
    WEBCLIENT_LOAD_ROUTES,
};
