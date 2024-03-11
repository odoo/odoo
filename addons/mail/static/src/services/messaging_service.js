/** @odoo-module **/

import { ModelManager } from '@mail/model/model_manager';

export const messagingService = {
    dependencies: [
        'effect',
        'bus_service',
        'localization',
        'messagingValues',
        'orm',
        'presence',
        'router',
        'rpc',
        'ui',
        'user',
    ],

    start(env, { messagingValues }) {
        const modelManager = new ModelManager(env);
        this._startModelManager(modelManager, messagingValues);

        return {
            /**
             * Returns the messaging record once it is initialized. This method
             * should be considered the main entry point to the messaging system
             * for outside code.
             *
             * @returns {mail.messaging}
             **/
            async get() {
                return modelManager.getMessaging();
            },
            modelManager,
        };
    },
    /**
     * Separate method to control creation delay in tests.
     *
     * @private
     */
    _startModelManager(modelManager, messagingValues) {
        modelManager.start(messagingValues);
    },
};
