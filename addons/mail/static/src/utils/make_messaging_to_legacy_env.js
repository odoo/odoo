
/** @odoo-module **/

export function makeMessagingToLegacyEnv(legacyEnv) {
    return {
        dependencies: ['messaging'],
        start(_, { messaging }) {
            legacyEnv.services.messaging = messaging;
        },
    };
}
