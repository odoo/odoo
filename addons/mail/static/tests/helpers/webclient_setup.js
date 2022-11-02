/** @odoo-module **/

import { setupBackendBus } from '@bus/setup/backend/setup_backend_helpers';

import { messagingService } from '@mail/services/messaging_service';
import { setupBackendMessaging } from '@mail/setup/backend/setup_backend_helpers';

import { registry } from '@web/core/registry';
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";

const ROUTES_TO_IGNORE = [
    '/web/webclient/load_menus',
    '/web/dataset/call_kw/res.users/load_views',
    '/web/dataset/call_kw/res.users/systray_get_activities'
];
const WEBCLIENT_PARAMETER_NAMES = new Set(['legacyParams', 'mockRPC', 'serverData', 'target', 'webClientClass']);
const SERVICES_PARAMETER_NAMES = new Set([
    'legacyServices', 'loadingBaseDelayDuration', 'messagingBeforeCreationDeferred',
    'messagingBus', 'services',
]);

/**
 * Setup messaging dependencies: services, main components, actions...
 *
 * @param {Object} param0
 * @param {Object} [param0.services]
 * @param {number} [param0.loadingBaseDelayDuration=0]
 * @param {Promise} [param0.messagingBeforeCreationDeferred=Promise.resolve()]
 *   Deferred that let tests block messaging creation and simulate resolution.
 *   Useful for testing components behavior when messaging is not yet created.
 * @param {EventBus} [param0.messagingBus]
 */
function setupMessagingDependencies({
    loadingBaseDelayDuration = 0,
    messagingBeforeCreationDeferred = Promise.resolve(),
    messagingBus,
    services = {},
 }) {
    patchWithCleanup(messagingService, {
        async _startModelManager(modelManager, messagingValues) {
            modelManager.isDebug = true;
            const _super = this._super.bind(this);
            await messagingBeforeCreationDeferred;
            return _super(modelManager, messagingValues);
        },
    });
    setupBackendBus();
    setupBackendMessaging({
        isInQUnitTest: true,
        disableAnimation: true,
        loadingBaseDelayDuration,
        messagingBus,
        userNotificationManager: { canPlayAudio: false },
    });

    const serviceRegistry = registry.category('services');
    Object.entries(services).forEach(([serviceName, service]) => {
        serviceRegistry.add(serviceName, service);
    });
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
 * @param {EventBus} [param0.messagingBus] The event bus to be used by messaging.
 * @returns {WebClient}
 */
 async function getWebClientReady(param0) {
    const servicesParameters = {};
    const param0Entries = Object.entries(param0);
    for (const [parameterName, value] of param0Entries) {
        if (SERVICES_PARAMETER_NAMES.has(parameterName)) {
            servicesParameters[parameterName] = value;
        }
    }
    setupMessagingDependencies(servicesParameters);

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
